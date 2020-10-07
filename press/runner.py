import json

from ansible import context
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.inventory.manager import InventoryManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Playbook
from ansible.plugins.callback import CallbackBase
from ansible.utils.display import Display
from ansible.vars.manager import VariableManager

import frappe


class AnsibleCallback(CallbackBase):
	def __init__(self, *args, **kwargs):
		super(AnsibleCallback, self).__init__(*args, **kwargs)

	def process_task_success(self, result):
		result, action = frappe._dict(result._result), result._task.action
		if action == "user":
			server_type, server = frappe.db.get_value(
				"Ansible Play", self.play, ["server_type", "server"]
			)
			server = frappe.get_doc(server_type, server)
			if result.name == "root":
				server.root_public_key = result.ssh_public_key
			elif result.name == "frappe":
				server.frappe_public_key = result.ssh_public_key
			server.save()

	def v2_runner_on_ok(self, result, *args, **kwargs):
		self.update_task("Success", result)
		self.process_task_success(result)

	def v2_runner_on_failed(self, result, *args, **kwargs):
		self.update_task("Failure", result)

	def v2_runner_on_skipped(self, result):
		self.update_task("Skipped", result)

	def v2_runner_on_unreachable(self, result):
		self.update_task("Unreachable", result)

	def v2_playbook_on_task_start(self, task, is_conditional):
		self.update_task("Running", None, task)

	def v2_playbook_on_start(self, playbook):
		self.update_play("Running")

	def v2_playbook_on_stats(self, stats):
		self.update_play(None, stats)

	def update_play(self, status=None, stats=None):
		play = frappe.get_doc("Ansible Play", self.play)
		if stats:
			# Assume we're running on one host
			host = list(stats.processed.keys())[0]
			play.update(stats.summarize(host))
			if play.failures or play.unreachable:
				play.status = "Failure"
			else:
				play.status = "Success"
		else:
			play.status = status

		play.save()
		frappe.db.commit()

	def update_task(self, status, result=None, task=None):
		if result:
			if not result._task._role:
				return
			task_name, result = self.parse_result(result)
		else:
			if not task._role:
				return
			task_name = self.tasks[task._role.get_name()][task.name]
		task = frappe.get_doc("Ansible Task", task_name)
		task.status = status
		if result:
			task.output = result.stdout
			task.error = result.stderr
			task.exception = result.msg
			# Reduce clutter be removing keys already shown elsewhere
			for key in ("stdout", "stdout_lines", "stderr", "stderr_lines", "msg"):
				result.pop(key, None)
			task.result = json.dumps(result, indent=4)
		task.save()
		frappe.db.commit()

	def parse_result(self, result):
		task = result._task.name
		role = result._task._role.get_name()
		return self.tasks[role][task], frappe._dict(result._result)


class Ansible:
	def __init__(self, server, playbook, variables=None):
		self.server = server
		self.playbook = playbook
		self.playbook_path = frappe.get_app_path("press", "playbooks", self.playbook)
		self.host = server.ip
		self.variables = variables or {}

		context.CLIARGS = ImmutableDict(
			become_method="sudo",
			check=False,
			connection="ssh",
			# This is the only way to pass variables that preserves newlines
			extra_vars=[f"{key}='{value}'" for key, value in self.variables.items()],
			remote_user="root",
			start_at_task=None,
			syntax=False,
			verbosity=3,
		)

		self.loader = DataLoader()
		self.passwords = dict({})

		self.sources = f"{self.host},"
		self.inventory = InventoryManager(loader=self.loader, sources=self.sources)
		self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

		self.callback = AnsibleCallback()
		self.display = Display()
		self.display.verbosity = 3
		self.create_ansible_play()

	def run(self):
		self.executor = PlaybookExecutor(
			playbooks=[self.playbook_path],
			inventory=self.inventory,
			variable_manager=self.variable_manager,
			loader=self.loader,
			passwords=self.passwords,
		)
		# Use AnsibleCallback so we can receive updates for tasks execution
		self.executor._tqm._stdout_callback = self.callback
		self.callback.play = self.play
		self.callback.tasks = self.tasks
		self.executor.run()
		return frappe.get_doc("Ansible Play", self.play)

	def create_ansible_play(self):
		# Parse the playbook and create Ansible Tasks so we can show how many tasks are pending
		playbook = Playbook.load(
			self.playbook_path, variable_manager=self.variable_manager, loader=self.loader
		)
		# Assume we only have one play per playbook
		play = playbook.get_plays()[0]
		play_doc = frappe.get_doc(
			{
				"doctype": "Ansible Play",
				"server_type": self.server.doctype,
				"server": self.server.name,
				"variables": json.dumps(self.variables, indent=4),
				"playbook": self.playbook,
				"play": play.get_name(),
			}
		).insert()
		self.play = play_doc.name
		self.tasks = {}
		for role in play.get_roles():
			for block in role.get_task_blocks():
				for task in block.block:
					task_doc = frappe.get_doc(
						{
							"doctype": "Ansible Task",
							"play": self.play,
							"role": role.get_name(),
							"task": task.name,
						}
					).insert()
					self.tasks.setdefault(role.get_name(), {})[task.name] = task_doc.name
