# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import shutil

import frappe
from ansible import constants, context
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory.manager import InventoryManager
from ansible.module_utils.common.collections import ImmutableDict
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars.manager import VariableManager
from frappe.model.document import Document

from press.utils import reconnect_on_failure


class SSHAccessAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.ssh_access_audit_host.ssh_access_audit_host import (
			SSHAccessAuditHost,
		)
		from press.infrastructure.doctype.ssh_access_audit_violation.ssh_access_audit_violation import (
			SSHAccessAuditViolation,
		)

		hosts: DF.Table[SSHAccessAuditHost]
		inventory: DF.Code | None
		name: DF.Int | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		violations: DF.Table[SSHAccessAuditViolation]
	# end: auto-generated types

	def before_insert(self):
		self.set_inventory()

	@frappe.whitelist()
	def run(self):
		frappe.only_for("System Manager")
		try:
			ad_hoc = AnsibleAdHoc(sources=self.inventory)
			for host in ad_hoc.run():
				self.append("hosts", host)
		except Exception:
			import traceback

			traceback.print_exc()
		self.save()

	def set_inventory(self):
		server_types = [
			"Proxy Server",
			"Server",
			"Database Server",
			"Analytics Server",
			"Log Server",
			"Monitor Server",
			"Registry Server",
			"Trace Server",
		]
		all_servers = []
		domain = frappe.db.get_value("Press Settings", None, "domain")
		for server_type in server_types:
			# Skip self-hosted servers
			filters = {"status": "Active", "domain": domain}
			meta = frappe.get_meta(server_type)
			if meta.has_field("cluster"):
				filters["cluster"] = ("!=", "Hybrid")

			if meta.has_field("is_self_hosted"):
				filters["is_self_hosted"] = False

			servers = frappe.get_all(server_type, filters=filters, pluck="name", order_by="creation asc")
			all_servers.extend(servers)

		all_servers.extend(self.get_self_inventory())
		self.inventory = ",".join(all_servers)

	def get_self_inventory(self):
		# Press should audit itself
		servers = [frappe.local.site, f"db.{frappe.local.site}"]
		if frappe.conf.replica_host:
			servers.append(f"db2.{frappe.local.site}")
		return servers


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

		self.callback = AnsibleCallback()

	def run(self):
		self.tasks = [
			{
				"action": {"module": "shell", "args": "grep '/bin/.*sh' /etc/passwd | cut -f 1,6 -d ':'"},
				"register": "users",
			},
			{
				"action": {"module": "shell", "args": "cat {{item.split(':')[1]}}/.ssh/authorized_keys"},
				"ignore_errors": True,
				"with_items": "{{users.stdout_lines}}",
			},
		]
		source = dict(
			name="Ansible Play",
			hosts="all",
			gather_facts="no",
			tasks=self.tasks,
		)

		self.play = Play().load(source, variable_manager=self.variable_manager, loader=self.loader)

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
			self.loader.cleanup_all_tmp_files()

		shutil.rmtree(constants.DEFAULT_LOCAL_TMP, True)

		return list(self.callback.hosts.values())


class AnsibleCallback(CallbackBase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.hosts = {}

	def v2_runner_on_ok(self, result, *args, **kwargs):
		self.update_task("Completed", result)

	def v2_runner_on_failed(self, result, *args, **kwargs):
		self.update_task("Completed", result)

	def v2_runner_on_unreachable(self, result):
		self.update_task("Unreachable", result)

	@reconnect_on_failure()
	def update_task(self, status, result):
		host, raw_result = self.parse_result(result)
		if raw_result:
			# Only update on the last task (that has results)
			users = []
			for row in raw_result:
				user = {
					"user": row["item"].split(":")[0],
					"command": row["cmd"],
					"keys": [],
				}
				for key in row["stdout_lines"]:
					if key.strip() and not key.strip().startswith("#"):
						user["keys"].append(key)

				users.append(user)

			self.hosts[host] = {
				"users": json.dumps(users, indent=1, sort_keys=True),
				"host": host,
				"status": status,
			}

		elif status == "Unreachable":
			self.hosts[host] = {"host": host, "status": status}

	def parse_result(self, result):
		host = result._host.get_name()
		_result = result._result
		return host, _result.get("results")
