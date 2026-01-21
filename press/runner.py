import json
import typing
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import frappe
import wrapt
from ansible import constants, context
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
from frappe.model.document import Document
from frappe.utils import cstr
from frappe.utils import now_datetime as now

from press.press.doctype.ansible_play.ansible_play import AnsiblePlay

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


def reconnect_on_failure():
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		try:
			return wrapped(*args, **kwargs)
		except Exception as e:
			if frappe.db.is_interface_error(e):
				frappe.db.connect()
				return wrapped(*args, **kwargs)
			raise

	return wrapper


class AnsibleCallback(CallbackBase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	@reconnect_on_failure()
	def process_task_success(self, result):
		result, action = frappe._dict(result._result), result._task.action
		if action == "user":
			server_type, server = frappe.db.get_value("Ansible Play", self.play, ["server_type", "server"])
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
			host = next(iter(stats.processed.keys()))
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
		self.publish_play_progress(task.name)
		frappe.db.commit()

	def publish_play_progress(self, task):
		frappe.publish_realtime(
			"ansible_play_progress",
			{"progress": self.task_list.index(task), "total": len(self.task_list), "play": self.play},
			doctype="Ansible Play",
			docname=self.play,
			user=frappe.session.user,
		)

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
		task_name = frappe.get_value("Ansible Task", {"play": self.play, "job_id": job_id}, "name")
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
		self.host = server.ip if server.ip else server.private_ip
		self.variables = variables or {}

		constants.HOST_KEY_CHECKING = False
		context.CLIARGS = ImmutableDict(
			become_method="sudo",
			check=False,
			connection="ssh",
			# This is the only way to pass variables that preserves newlines
			extra_vars=[f"{cstr(key)}='{cstr(value)}'" for key, value in self.variables.items()],
			remote_user=user,
			start_at_task=None,
			syntax=False,
			verbosity=1,
			ssh_common_args=self._get_ssh_proxy_commad(server),
		)

		self.loader = DataLoader()
		self.passwords = dict({})

		self.sources = f"{self.host},"
		self.inventory = InventoryManager(loader=self.loader, sources=self.sources)
		self.inventory.get_host(self.host).set_variable("ansible_port", port)

		self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

		self.callback = AnsibleCallback()
		self.display = Display()
		self.display.verbosity = 1
		self.create_ansible_play()

	def _get_ssh_proxy_commad(self, server):
		# Note: ProxyCommand must be enclosed in double quotes
		# because it contains spaces
		# and the entire argument must be enclosed in single quotes
		# because it is passed via the CLI
		# See https://docs.ansible.com/ansible/latest/user_guide/connection_details.html#ssh-args
		# and https://unix.stackexchange.com/a/303717
		# for details
		proxy_command = None
		if hasattr(self.server, "bastion_host") and self.server.bastion_host:
			proxy_command = f'-o ProxyCommand="ssh -W %h:%p \
					{server.bastion_host.ssh_user}@{server.bastion_host.ip} \
						-p {server.bastion_host.ssh_port}"'

		return proxy_command

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

	def run(self) -> AnsiblePlay:
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
		self.callback.task_list = self.task_list
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
		self.task_list = []
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
					self.task_list.append(task_doc.name)


class Status(str, Enum):
	Pending = "Pending"
	Running = "Running"
	Success = "Success"
	Skipped = "Skipped"
	Failure = "Failure"

	def __str__(self):
		return self.value


class GenericStep(Document):
	attempt: int
	job_type: Literal["Ansible Play", "Agent Job"]
	job: str | None
	status: Status
	method_name: str


@dataclass
class StepHandler:
	save: Callable
	reload: Callable
	doctype: str
	name: str

	def handle_vm_status_job(
		self,
		step: GenericStep,
		virtual_machine: str,
		expected_status: str,
	) -> None:
		step.attempt = 1 if not step.attempt else step.attempt + 1

		# Try to sync status in every attempt
		try:
			virtual_machine_doc: "VirtualMachine" = frappe.get_doc("Virtual Machine", virtual_machine)
			virtual_machine_doc.sync()
		except Exception:
			pass

		machine_status = frappe.db.get_value("Virtual Machine", virtual_machine, "status")
		step.status = Status.Running if machine_status != expected_status else Status.Success
		step.save()

	def handle_agent_job(self, step: GenericStep, job: str, poll: bool = False) -> None:
		if poll:
			job_doc: AgentJob = frappe.get_doc("Agent Job", job)
			job_doc.get_status()

		job_status = frappe.db.get_value("Agent Job", job, "status")

		status_map = {
			"Delivery Failure": Status.Failure,
			"Undelivered": Status.Pending,
		}
		job_status = status_map.get(job_status, job_status)
		step.attempt = 1 if not step.attempt else step.attempt + 1

		step.status = job_status
		step.save()

		if step.status == Status.Failure:
			raise

	def handle_ansible_play(self, step: GenericStep, ansible: Ansible) -> None:
		step.job_type = "Ansible Play"
		step.job = ansible.play
		step.save()
		ansible_play = ansible.run()
		step.status = ansible_play.status
		step.save()

		if step.status == Status.Failure:
			raise

	def _fail_ansible_step(
		self,
		step: GenericStep,
		ansible: Ansible,
		e: Exception | None = None,
	) -> None:
		step.job = getattr(ansible, "play", None)
		step.status = Status.Failure
		step.output = str(e)
		step.save()

	def _fail_job_step(self, step: GenericStep, e: Exception | None = None) -> None:
		step.status = Status.Failure
		step.output = str(e)
		step.save()

	def fail(self):
		self.status = Status.Failure
		self.save()
		frappe.db.commit()

	def succeed(self):
		self.status = Status.Success
		self.save()
		frappe.db.commit()

	def handle_step_failure(self):
		# can be implemented by the controller
		pass

	def get_steps(self, methods: list) -> list[dict]:
		"""Generate a list of steps to be executed for NFS volume attachment."""
		return [
			{
				"step_name": method.__doc__,
				"method_name": method.__name__,
				"status": "Pending",
			}
			for method in methods
		]

	def _get_method(self, method_name: str):
		"""Retrieve a method object by name."""
		return getattr(self, method_name)

	def next_step(self, steps: list[GenericStep]) -> GenericStep | None:
		for step in steps:
			if step.status not in (Status.Success, Status.Failure, Status.Skipped):
				return step

		return None

	def _execute_steps(self, steps: list[GenericStep]):
		"""It is now required to be with a `enqueue_doc` else the first step executes in the web worker"""
		self.status = Status.Running
		self.save()
		frappe.db.commit()

		step = self.next_step(steps)
		if not step:
			self.succeed()
			return

		# Run a single step in this job
		step = step.reload()
		method = self._get_method(step.method_name)

		try:
			method(step)
			frappe.db.commit()
		except Exception:
			self.reload()
			self.fail()
			self.handle_step_failure()
			frappe.db.commit()
			return

		# After step completes, queue the next step
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_execute_steps",
			steps=steps,
			timeout=18000,
			at_front=True,
			queue="long",
			enqueue_after_commit=True,
		)
