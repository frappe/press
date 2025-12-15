from __future__ import annotations

import contextlib
import json
import subprocess
import tempfile
import typing
from dataclasses import dataclass
from enum import Enum
from typing import Literal

import ansible_runner
import frappe
import wrapt
from ansible.inventory.manager import os
from frappe.model.document import Document
from frappe.utils import get_datetime
from frappe.utils import now_datetime as now

if typing.TYPE_CHECKING:
	from collections.abc import Callable

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.ansible_play.ansible_play import AnsiblePlay
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


def reconnect_on_failure():
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		_ = instance
		try:
			return wrapped(*args, **kwargs)
		except Exception as e:
			if frappe.db.is_interface_error(e):  # type: ignore
				frappe.db.connect()
				return wrapped(*args, **kwargs)
			raise

	return wrapper


# Ansible Play Handler Implementation


class Ansible:
	def __init__(
		self,
		server: Server,
		playbook: str,
		user="root",
		variables: dict | None = None,
		port: int = 22,
		debug: bool = False,
	):
		self.server = server
		self.host = self.server.ip
		self.port = port
		self.playbook = playbook
		self.playbook_path = frappe.get_app_path("press", "playbooks", self.playbook)
		self.variables = variables or {}
		self.user = user
		self.debug = debug
		self.create_ansible_play()

	def create_ansible_play(self):
		# Parse the playbook and create Ansible Tasks so we can show how many tasks are pending
		# Assume we only have one play per playbook
		play = self._get_play()
		play_doc = frappe.get_doc(
			{
				"doctype": "Ansible Play",
				"server_type": self.server.doctype,
				"server": self.server.name,
				"variables": json.dumps(self.variables, indent=4),
				"playbook": self.playbook,
				"play": play["name"],
			}
		).insert()
		self.play = play_doc.name
		self.tasks = {}
		self.task_list = []
		for task in play["tasks"]:
			task_doc = frappe.get_doc(
				{
					"doctype": "Ansible Task",
					"play": self.play,
					"role": task["role"],
					"task": task["task"],
				}
			).insert()
			self.tasks.setdefault(task["role"], {})[task["task"]] = task_doc.name
			self.task_list.append(task_doc.name)

	def run(self):
		# Note: ansible-runner sets awx_display as the DisplayCallBack
		# awx_display listens to the ansible output and emits events for easier consumption

		ansible_runner.run(
			playbook=self.playbook_path,
			inventory=f"{self.host}:{self.port}",
			extravars=self.variables,
			cmdline=self.generate_cmdline(),
			event_handler=self.event_handler,
			quiet=(not self.debug),
			verbosity=0 if self.debug else 1,
		)
		assert self.play, "Play not found"
		return frappe.get_doc("Ansible Play", self.play)

	def generate_cmdline(self):
		cmdline = f"--user={self.user}"
		# Note: ProxyCommand must be enclosed in double quotes
		# because it contains spaces
		# and the entire argument must be enclosed in single quotes
		# because it is passed via the CLI
		# See https://docs.ansible.com/ansible/latest/user_guide/connection_details.html#ssh-args
		# and https://unix.stackexchange.com/a/303717
		# for details
		if hasattr(self.server, "bastion_host") and self.server.bastion_host:
			cmdline += (
				f' -o ProxyCommand="ssh -W %h:%p '
				f"{self.server.bastion_host.ssh_user}@{self.server.bastion_host.ip}"
				f'-p {self.server.bastion_host.ssh_port}"'
			)
		return cmdline

	def event_handler(self, event):
		event_type = event.get("event")
		if hasattr(self, event_type):
			method = getattr(self, event_type)
			if callable(method):
				method(event.get("event_data"))

	def playbook_on_start(self, event):
		self.update_play("Running")

	def playbook_on_stats(self, event):
		stats = {}
		for key in ["changed", "dark", "failures", "ignored", "ok", "processed", "rescued", "skipped"]:
			stats[key] = event.get(key, {}).get(self.server, 0)
		stats["unreachable"] = stats.pop("dark", 0)  # ansible_runner quirk
		self.update_play(stats=stats)

	def playbook_on_task_start(self, event):
		self.update_task("Running", task=event)

	def runner_on_ok(self, event):
		self.update_task("Success", event)
		self.process_task_success(event)

	def runner_on_failed(self, event):
		self.update_task("Failure", result=event)

	def runner_on_skipped(self, event):
		self.update_task("Skipped", result=event)

	def runner_on_unreachable(self, event):
		self.update_task("Unreachable", result=event)

	@reconnect_on_failure()
	def process_task_success(self, event):
		result, action = frappe._dict(event.get("res", {})), event.get("task_action")
		if action == "user" and self.play:
			server_type, server = frappe.db.get_value("Ansible Play", self.play, ["server_type", "server"])  # type: ignore
			server = frappe.get_doc(server_type, server)  # type: ignore
			if result.name == "root":
				server.root_public_key = result.ssh_public_key  # type: ignore
			elif result.name == "frappe":
				server.frappe_public_key = result.ssh_public_key  # type: ignore
			server.save()

	@reconnect_on_failure()
	def update_play(
		self, status: Literal["Pending", "Running", "Success", "Failure"] | None = None, stats=None
	):
		assert self.play, "Play not found"
		play: AnsiblePlay = frappe.get_doc("Ansible Play", self.play)  # type: ignore
		if stats:
			play.update(stats)
			if play.failures or play.unreachable:
				play.status = "Failure"
			else:
				play.status = "Success"
			play.end = now()
			start = get_datetime(play.start)
			end = get_datetime(play.end)
			assert start and end, "Start and end times not found"
			play.duration = int((end - start).total_seconds())  # type: ignore
		else:
			assert status, "Status not found"
			play.status = status
			play.start = now()

		play.save()
		frappe.db.commit()

	@reconnect_on_failure()
	def update_task(self, status, result: dict | None = None, task: dict | None = None):
		parsed = None
		if result:
			role, name = result.get("role"), result.get("task")
			parsed = frappe._dict(result.get("res", {}))
		elif task:
			role, name = task.get("role"), task.get("task")
		else:
			raise ValueError("Either result or task must be provided")

		if not role or not name:
			return

		task_name = self.tasks[role][name]
		task_doc: AnsibleTask = frappe.get_doc("Ansible Task", task_name)  # type: ignore
		task_doc.status = status

		if parsed:
			task_doc.output = parsed.stdout
			task_doc.error = parsed.stderr
			task_doc.exception = parsed.msg
			# Reduce clutter be removing keys already shown elsewhere
			for key in ("stdout", "stdout_lines", "stderr", "stderr_lines", "msg"):
				assert result, f"Result is None for task {task_name}"
				result.pop(key, None)
			task_doc.result = json.dumps(result, indent=4)
			task_doc.end = now()

			start = get_datetime(task_doc.start)
			end = get_datetime(task_doc.end)
			assert start and end, f"Start or end is None for task {task_name}"
			task_doc.duration = int((end - start).total_seconds())
		else:
			task_doc.start = now()
		task_doc.save()
		self._publish_play_progress(task_doc.name)
		frappe.db.commit()

	def _get_play(self):
		return self._parse_tasks(self._get_task_list())

	def _parse_tasks(self, list_tasks_output):  # noqa: C901
		"""Parse the output of ansible-playbook --list-tasks to get the play name and tasks."""
		ROLE_SEPARATOR = " : "
		TAG_SEPARATOR = "TAGS: "
		PLAY_SEPARATOR = " (all): "

		def parse_parts(line, name_separator):
			first, second = None, None
			if name_separator in line and TAG_SEPARATOR in line:
				# Split on the first name_separator to get name
				parts = line.split(name_separator, 1)
				if len(parts) == 2:
					first = parts[0].strip()

					# Remove the TAGS part
					second_part = parts[1].strip()
					if TAG_SEPARATOR in second_part:
						second = second_part.split(TAG_SEPARATOR)[0].strip()
			return first, second

		parsed = {"name": None, "tasks": []}
		lines = list_tasks_output.strip().split("\n")

		for line in lines:
			line = line.strip()

			# Skip empty lines, playbook header and tasks header
			if not line or (line.startswith("playbook:") and line == "tasks:"):
				continue

			# Parse the play name
			if line.startswith("play #"):
				_, play = parse_parts(line, PLAY_SEPARATOR)
				if play:
					parsed["name"] = play
				continue

			# Process task lines that contain role and task information
			if ROLE_SEPARATOR in line and TAG_SEPARATOR in line:
				role, task = parse_parts(line, ROLE_SEPARATOR)
				if role and task:
					parsed["tasks"].append({"role": role, "task": task})

		return parsed

	def _get_task_list(self):
		return subprocess.check_output(["ansible-playbook", self.playbook_path, "--list-tasks"]).decode(
			"utf-8"
		)

	def _publish_play_progress(self, task):
		frappe.publish_realtime(
			"ansible_play_progress",
			{"progress": self.task_list.index(task), "total": len(self.task_list), "play": self.play},
			doctype="Ansible Play",
			docname=self.play,
			user=frappe.session.user,
		)


# Ansible AdHoc Command Runner


class AnsibleAdHoc:
	def __init__(
		self,
		sources: str | list[str],
		nonce: str | None = None,
		port: int = 22,
		user: str = "root",
		on_publish: Callable[[str | None, list], None] | None = None,
	):
		"""
		Run command on remote hosts.
		Args:
			sources: List of hosts or comma-separated string of hosts
			nonce: Random ID for tracking
			port: SSH port (default: 22).
			user: SSH user (default: root).
			on_publish: Callback function to publish progress
		"""
		if isinstance(sources, str):
			sources = [s.strip() for s in sources.split(",")]
		if not sources:
			raise ValueError("Hosts must be provided")

		self.hosts = sources
		self.port = port
		self.user = user
		self.nonce = nonce
		self.results: dict[str, dict] = {}

		self.on_publish = on_publish

	def run(
		self,
		command: str,
		module: str = "shell",
		variables: dict | None = None,
		become: bool = True,
		raw_params: bool = True,
	):
		# Create a temporary directory for ansible-runner
		with tempfile.TemporaryDirectory() as private_data_dir:
			# Create inventory
			inventory_content = self._create_inventory()
			inventory_path = os.path.join(private_data_dir, "inventory")
			os.makedirs(inventory_path)

			with open(os.path.join(inventory_path, "hosts"), "w") as f:
				f.write(inventory_content)

			# Build module arguments
			# raw_params tells Ansible to pass the command string directly without parsing (Useful for command with complex grep)
			if raw_params and (module == "shell" or module == "command"):
				# Use _raw_params for shell/command modules when raw_params is True
				module_args = f"_raw_params={command}"
			if module == "shell" or module == "command":
				module_args = command
			else:
				# For other modules, parse command as key=value pairs or use as-is
				module_args = command

			# Build cmdline options
			cmdline_parts = [f"--user={self.user}"]
			if become:
				cmdline_parts.append("--become")

			cmdline = " ".join(cmdline_parts)

			# Run the ad-hoc command
			ansible_runner.run(
				private_data_dir=private_data_dir,
				host_pattern="all",
				module=module,
				module_args=module_args,
				inventory=inventory_path,
				extravars=variables or {},
				cmdline=cmdline,
				event_handler=self.event_handler,
			)

			# Process final results
			return self._format_results()

	def _create_inventory(self) -> str:
		lines = ["[targets]"]
		for host in self.hosts:
			if self.port != 22:
				lines.append(f"{host} ansible_port={self.port}")
			else:
				lines.append(host)

		return "\n".join(lines)

	def event_handler(self, event):
		event_type = event.get("event")

		if event_type == "runner_on_ok":
			self._handle_ok(event.get("event_data", {}))
		elif event_type == "runner_on_failed":
			self._handle_failed(event.get("event_data", {}))
		elif event_type == "runner_on_unreachable":
			self._handle_unreachable(event.get("event_data", {}))
		elif event_type == "runner_on_skipped":
			self._handle_skipped(event.get("event_data", {}))

	@reconnect_on_failure()
	def _handle_ok(self, event_data):
		host = event_data.get("host")
		result = frappe._dict(event_data.get("res", {}))

		self.results[host] = {
			"host": host,
			"status": "Success",
			"output": result.get("stdout", ""),
			"error": result.get("stderr", ""),
			"exception": result.get("msg", ""),
			"exit_code": result.get("rc"),
			"changed": result.get("changed", False),
			"duration": self._parse_duration(result.get("delta")),
		}
		self._publish_update()

	@reconnect_on_failure()
	def _handle_failed(self, event_data):
		host = event_data.get("host")
		result = frappe._dict(event_data.get("res", {}))

		self.results[host] = {
			"host": host,
			"status": "Failure",
			"output": result.get("stdout", ""),
			"error": result.get("stderr", ""),
			"exception": result.get("msg", ""),
			"exit_code": result.get("rc"),
			"changed": result.get("changed", False),
			"duration": self._parse_duration(result.get("delta")),
		}
		self._publish_update()

	@reconnect_on_failure()
	def _handle_unreachable(self, event_data):
		host = event_data.get("host")
		result = frappe._dict(event_data.get("res", {}))

		self.results[host] = {
			"host": host,
			"status": "Unreachable",
			"output": "",
			"error": "",
			"exception": result.get("msg", "Host unreachable"),
			"exit_code": None,
			"changed": False,
			"duration": 0,
		}
		self._publish_update()

	@reconnect_on_failure()
	def _handle_skipped(self, event_data):
		host = event_data.get("host")

		self.results[host] = {
			"host": host,
			"status": "Skipped",
			"output": "",
			"error": "",
			"exception": "Task skipped",
			"exit_code": None,
			"changed": False,
			"duration": 0,
		}
		self._publish_update()

	def _parse_duration(self, delta):
		if not delta:
			return 0

		try:
			# Delta is usually in format like "0:00:01.234567"
			parts = delta.split(":")
			hours = int(parts[0])
			minutes = int(parts[1])
			seconds = float(parts[2])
			return int(hours * 3600 + minutes * 60 + seconds)
		except (ValueError, IndexError):
			return 0

	def _publish_update(self):
		if not self.on_publish:
			return

		with contextlib.suppress(Exception):
			self.on_publish(self.nonce, list(self.results.values()))

	def _format_results(self):
		return list(self.results.values())


# Step Handler Implementation


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
			virtual_machine_doc: "VirtualMachine" = frappe.get_doc("Virtual Machine", virtual_machine)  # type: ignore
			virtual_machine_doc.sync()
		except Exception:
			pass

		machine_status = frappe.db.get_value("Virtual Machine", virtual_machine, "status")
		step.status = Status.Running if machine_status != expected_status else Status.Success
		step.save()

	def handle_agent_job(self, step: GenericStep, job: str, poll: bool = False) -> None:
		if poll:
			job_doc: AgentJob = frappe.get_doc("Agent Job", job)  # type: ignore
			job_doc.get_status()

		job_status = frappe.db.get_value("Agent Job", job, "status")

		status_map: dict = {
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
		step.status = ansible_play.status  # type: ignore
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
		step.output = str(e)  # type: ignore
		step.save()

	def _fail_job_step(self, step: GenericStep, e: Exception | None = None) -> None:
		step.status = Status.Failure
		step.output = str(e)  # type: ignore
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
