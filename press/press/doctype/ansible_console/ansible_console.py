# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re

import frappe
from ansible import constants, context
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_timedelta

from press.access.server_console import (
	CONSOLE_DOCTYPES,
	check_console_access,
	check_console_role,
	has_system_manager_role,
)
from press.press.doctype.virtual_machine.virtual_machine import SERIES_TO_SERVER_TYPE
from press.utils import reconnect_on_failure

# A host of Ansible's host_list inventory that is a plain name: no port, range, pattern or path.
HOST_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")


class AnsibleConsole(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.ansible_console_output.ansible_console_output import (
			AnsibleConsoleOutput,
		)

		command: DF.Code | None
		error: DF.Code | None
		inventory: DF.Code | None
		nonce: DF.Data | None
		output: DF.Table[AnsibleConsoleOutput]
	# end: auto-generated types

	def run(self):
		self.inventory = check_inventory_access(self.inventory)
		try:
			ad_hoc = AnsibleAdHoc(sources=self.inventory)
			for host in ad_hoc.run(self.command, self.nonce, raw_params=True):
				self.append("output", host)
		except Exception:
			self.error = frappe.get_traceback()
			import traceback

			traceback.print_exc()
		log = self.as_dict()
		# The log belongs to whoever ran it: staff read only their own logs.
		log.update({"doctype": "Ansible Console Log", "owner": frappe.session.user})
		frappe.get_doc(log).insert(ignore_permissions=True)
		frappe.db.commit()


def check_inventory_access(inventory: str | None) -> str | None:
	"""The inventory to run. Staff without System Manager list only servers they can reach."""
	check_console_role()
	if has_system_manager_role():
		return inventory
	hosts = parse_hosts(inventory)
	for host in hosts:
		check_console_access(find_server_doctype(host), host)
	return ",".join(hosts) + ","


def parse_hosts(inventory: str | None) -> list[str]:
	"""The host names of a comma-separated inventory. Anything else Ansible reads differently."""
	hosts = [host.strip() for host in (inventory or "").split(",") if host.strip()]
	if not hosts or not all(HOST_NAME.match(host) for host in hosts):
		frappe.throw(
			_(
				"List servers by name, separated by commas. Groups, patterns, ranges, ports and files are not allowed: {0}"
			).format(inventory or ""),
			frappe.PermissionError,
		)
	return hosts


def find_server_doctype(host: str) -> str:
	"""The DocType of the one server named `host`."""
	doctypes = [doctype for doctype in CONSOLE_DOCTYPES if frappe.db.exists(doctype, host) == host]
	if len(doctypes) != 1:
		frappe.throw(
			_("{0} is not the name of a Server, Database Server or Proxy Server").format(host),
			frappe.PermissionError,
		)
	return doctypes[0]


@frappe.whitelist()
def execute_command(doc):
	check_inventory_access(parse_console(doc).inventory)
	frappe.enqueue(
		"press.press.doctype.ansible_console.ansible_console._execute_command",
		doc=doc,
		timeout=7200,
	)
	return doc


def _execute_command(doc):
	console = parse_console(doc)
	console.run()
	return console.as_dict()


def parse_console(doc) -> AnsibleConsole:
	values = frappe.parse_json(doc)
	if not isinstance(values, dict) or values.get("doctype") != "Ansible Console":
		frappe.throw(_("Send an Ansible Console document"), frappe.PermissionError)
	return AnsibleConsole(values)


class AnsibleCallback(CallbackBase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.hosts = {}

	def v2_runner_on_ok(self, result, *args, **kwargs):
		self.update_task("Success", result)

	def v2_runner_on_failed(self, result, *args, **kwargs):
		self.update_task("Failure", result)

	def v2_runner_on_unreachable(self, result):
		self.update_task("Unreachable", result)

	@reconnect_on_failure()
	def update_task(self, status, result):
		host, result = self.parse_result(result)
		result.update(
			{
				"host": host,
				"status": status,
			}
		)
		self.hosts[host] = result
		self.publish_update()

	def parse_result(self, result):
		host = result._host.get_name()
		_result = result._result
		return host, frappe._dict(
			{
				"output": _result.get("stdout"),
				"error": _result.get("stderr"),
				"exception": _result.get("msg"),
				"exit_code": _result.get("rc"),
				"duration": get_timedelta(_result.get("delta", "0:00:00.000000")),
			}
		)

	def publish_update(self):
		message = {"nonce": self.nonce, "output": list(self.hosts.values())}
		frappe.publish_realtime(
			event="ansible_console_update",
			doctype="Ansible Console",
			docname="Ansible Console",
			user=frappe.session.user,
			message=message,
		)


class AnsibleAdHoc:
	def __init__(self, sources):
		constants.HOST_KEY_CHECKING = False
		context.CLIARGS = ImmutableDict(
			become_method="sudo",
			check=False,
			connection="ssh",
			extra_vars=[],
			remote_user="root",
			start_at_task=None,
			syntax=False,
			verbosity=3,
		)

		self.loader = DataLoader()
		self.passwords = dict({})

		self.inventory = InventoryManager(loader=self.loader, sources=sources)
		self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)

		self._apply_proxy_configurations(self._fetch_proxy_mapping(sources))
		self.callback = self._callback()

	def _callback(self):
		return AnsibleCallback()

	def run(self, command, nonce=None, raw_params: bool = False, become_user: str = "root"):
		shell_command_args = command
		if raw_params:
			shell_command_args = {
				"_raw_params": command,
			}
		self.tasks = [
			dict(action=dict(module="shell", args=shell_command_args), become=True, become_user=become_user)
		]
		source = dict(
			name="Ansible Play",
			hosts="all",
			gather_facts="no",
			tasks=self.tasks,
		)

		self.play = Play().load(source, variable_manager=self.variable_manager, loader=self.loader)

		self.callback.nonce = nonce

		tqm = TaskQueueManager(
			inventory=self.inventory,
			variable_manager=self.variable_manager,
			loader=self.loader,
			passwords=self.passwords,
			stdout_callback=self.callback,
			forks=16,
		)

		try:
			tqm.run(self.play)
		finally:
			tqm.cleanup()

		self.callback.publish_update()
		return list(self.callback.hosts.values())

	def _fetch_proxy_mapping(self, sources):  # noqa: C901
		proxy_map = {}
		source_list = list(set(s.strip() for s in sources.split(",") if s.strip()))
		if not source_list:
			return proxy_map

		multiple_char_server_type = [k for k in SERIES_TO_SERVER_TYPE if len(k) > 1]

		type_to_sources = {}
		for src in source_list:
			matched_key = next((k for k in multiple_char_server_type if src.startswith(k)), None)
			server_type = (
				SERIES_TO_SERVER_TYPE.get(matched_key) if matched_key else SERIES_TO_SERVER_TYPE.get(src[0])
			)
			if not server_type:
				continue

			type_to_sources.setdefault(server_type, []).append(src)

		all_servers = []
		for server_type, names in type_to_sources.items():
			try:
				servers = frappe.get_all(
					server_type,
					filters={"name": ["in", names]},
					fields=["name", "cluster", "ip", "private_ip"],
				)
				all_servers.extend(servers)
			except frappe.db.OperationalError:
				# Handles cases where 'cluster' might not exist in the schema
				continue

		cluster_cache = {}
		clusters = [s.cluster for s in all_servers if not s.ip and s.private_ip and s.cluster]
		if clusters:
			proxies = frappe.get_all(
				"Proxy Server",
				filters={"status": "Active", "cluster": ["in", clusters]},
				fields=["name", "cluster"],
			)
			cluster_cache = {p.cluster: p.name for p in proxies}

		for server in all_servers:
			if not server.ip and server.private_ip and server.cluster:
				proxy_name = cluster_cache.get(server.cluster)
				if proxy_name:
					proxy_map[server.name] = proxy_name

		return proxy_map

	def _apply_proxy_configurations(self, proxy_map):
		"""Applies SSH ProxyJump arguments to the Ansible variable manager."""
		for target, proxy in proxy_map.items():
			host = self.inventory.get_host(target)
			if host:
				ssh_args = f'-o ProxyCommand="ssh -W %h:%p root@{proxy}"'
				self.variable_manager.set_host_variable(host.get_name(), "ansible_ssh_common_args", ssh_args)
