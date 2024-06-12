import json

import wrapt
from ansible import context
from ansible import constants
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.executor.task_executor import TaskExecutor
from ansible.inventory.manager import InventoryManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Playbook
from ansible.plugins.action.async_status import ActionModule
from ansible.plugins.callback import CallbackBase
from ansible.utils.display import Display
from ansible.vars.manager import VariableManager
from pymysql.err import InterfaceError

import frappe
from frappe.utils import now_datetime as now


def reconnect_on_failure():
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		try:
			return wrapped(*args, **kwargs)
		except InterfaceError:
			frappe.db.connect()
			return wrapped(*args, **kwargs)

	return wrapper


class AnsibleCallback(CallbackBase):
	def __init__(self, *args, **kwargs):
		super(AnsibleCallback, self).__init__(*args, **kwargs)

	@reconnect_on_failure()
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

	@reconnect_on_failure()
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
			play.end = now()
			play.duration = play.end - play.start
		else:
			play.status = status
			play.start = now()

		play.save()
		frappe.db.commit()

	@reconnect_on_failure()
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
			task.end = now()
			task.duration = task.end - task.start
		else:
			task.start = now()
		task.save()
		frappe.db.commit()

	def parse_result(self, result):
		task = result._task.name
		role = result._task._role.get_name()
		return self.tasks[role][task], frappe._dict(result._result)

	@reconnect_on_failure()
	def on_async_start(self, role, task, job_id):
		task_name = self.tasks[role][task]
		task = frappe.get_doc("Ansible Task", task_name)
		task.job_id = job_id
		task.save()
		frappe.db.commit()

	@reconnect_on_failure()
	def on_async_poll(self, result):
		job_id = result["ansible_job_id"]
		task_name = frappe.get_value(
			"Ansible Task", {"play": self.play, "job_id": job_id}, "name"
		)
		task = frappe.get_doc("Ansible Task", task_name)
		task.result = json.dumps(result, indent=4)
		task.duration = now() - task.start
		task.save()
		frappe.db.commit()


class Ansible:
	def __init__(self, server, playbook, user="root", variables=None, port=22):
		self.patch()
		self.server = server
		self.playbook = playbook
		self.playbook_path = frappe.get_app_path("press", "playbooks", self.playbook)
		self.host = f"{server.ip}:{port}"
		self.variables = variables or {}

		constants.HOST_KEY_CHECKING = False
		context.CLIARGS = ImmutableDict(
			become_method="sudo",
			check=False,
			connection="ssh",
			# This is the only way to pass variables that preserves newlines
			extra_vars=[f"{key}='{value}'" for key, value in self.variables.items()],
			remote_user=user,
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

	def patch(self):
		def modified_action_module_run(*args, **kwargs):
			result = self.action_module_run(*args, **kwargs)
			self.callback.on_async_poll(result)
			return result

		def modified_poll_async_result(executor, result, templar, task_vars=None):
			job_id = result["ansible_job_id"]
			task = executor._task
			self.callback.on_async_start(task._role.get_name(), task.name, job_id)
			return self._poll_async_result(executor, result, templar, task_vars=task_vars)

		if ActionModule.run.__module__ != "press.runner":
			self.action_module_run = ActionModule.run
			ActionModule.run = modified_action_module_run

		if TaskExecutor.run.__module__ != "press.runner":
			self._poll_async_result = TaskExecutor._poll_async_result
			TaskExecutor._poll_async_result = modified_poll_async_result

	def unpatch(self):
		TaskExecutor._poll_async_result = self._poll_async_result
		ActionModule.run = self.action_module_run

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
		self.unpatch()
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
