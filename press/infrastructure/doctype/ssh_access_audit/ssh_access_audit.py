# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from functools import cached_property

import frappe
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.playbook.play import Play
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc, AnsibleCallback
from press.utils import reconnect_on_failure

SERVER_TYPES = [
	"Proxy Server",
	"Server",
	"Database Server",
	"Analytics Server",
	"Log Server",
	"Monitor Server",
	"Registry Server",
	"Trace Server",
	"NAT Server",
]


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
		known_violations: DF.Table[SSHAccessAuditViolation]
		name: DF.Int | None
		reachable_hosts: DF.Int
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		suspicious_users: DF.Code | None
		total_hosts: DF.Int
		total_known_violations: DF.Int
		total_violations: DF.Int
		user_violations: DF.Int
		violations: DF.Table[SSHAccessAuditViolation]
	# end: auto-generated types

	def before_insert(self):
		self.set_inventory()

	@frappe.whitelist()
	def run(self):
		frappe.only_for("System Manager")
		self.status = "Running"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_run", queue="long", timeout=3600, enqueue_after_commit=True
		)

	def _run(self):
		self.fetch_keys_from_servers()
		self.check_key_violations()
		self.check_user_violations()
		self.set_statistics()
		self.set_status()
		self.save()

	def fetch_keys_from_servers(self):
		try:
			ad_hoc = SSHAdHoc(sources=self.inventory)
			hosts = ad_hoc.run()
			sorted_hosts = sorted(hosts, key=lambda host: self.inventory.index(host["host"]))
			for host in sorted_hosts:
				self.append("hosts", host)
		except Exception:
			import traceback

			traceback.print_exc()

	def set_inventory(self):
		all_servers = []
		domain = frappe.db.get_value("Press Settings", None, "domain")
		for server_type in SERVER_TYPES:
			# Skip self-hosted servers
			filters = {"status": "Active", "domain": domain}
			fields = ("ip", "private_ip")
			meta = frappe.get_meta(server_type)
			if meta.has_field("cluster"):
				filters["cluster"] = ("!=", "Hybrid")
				fields.add("cluster")

			if meta.has_field("is_self_hosted"):
				filters["is_self_hosted"] = False

			servers = frappe.get_all(server_type, filters=filters, fields=fields)
			all_servers.extend(servers)

		all_servers.extend(self.get_self_inventory())
		self.inventory = all_servers

	def get_self_inventory(self):
		# Press should audit itself
		servers = [{"name": frappe.local.site}, {"name": f"db.{frappe.local.site}"}]
		if frappe.conf.replica_host:
			servers.append({"name": f"db2.{frappe.local.site}"})
		return servers

	def get_acceptable_key_fields(self):
		fields = []
		for server_type in SERVER_TYPES:
			meta = frappe.get_meta(server_type)
			for key_field in ["root_public_key", "frappe_public_key"]:
				if meta.has_field(key_field):
					fields.append([server_type, key_field])

		fields.append(["SSH Key", "public_key"])
		return fields

	def get_known_key_fields(self):
		fields = self.get_acceptable_key_fields()
		fields.append(["User SSH Key", "ssh_public_key"])
		return fields

	@cached_property
	def acceptable_keys(self):
		keys = {}
		domain = frappe.db.get_value("Press Settings", None, "domain")
		fields = self.get_acceptable_key_fields()
		for doctype, field in fields:
			filters = {}
			if doctype.endswith("Server"):  # Skip self-hosted servers
				filters = {"status": "Active", "domain": domain}

				meta = frappe.get_meta(doctype)
				if meta.has_field("cluster"):
					filters["cluster"] = ("!=", "Hybrid")

				if meta.has_field("is_self_hosted"):
					filters["is_self_hosted"] = False

			documents = frappe.get_all(doctype, filters=filters, fields=["name", field])
			for document in documents:
				key_string = document.get(field)
				if not key_string:
					continue
				key = _extract_key_from_key_string(key_string)
				keys[key] = {
					"key_doctype": doctype,
					"key_document": document.name,
					"key_field": field,
				}
		return keys

	@cached_property
	def known_keys(self):
		keys = {}
		fields = self.get_known_key_fields()
		for doctype, field in fields:
			documents = frappe.get_all(doctype, fields=["name", field])
			for document in documents:
				key_string = document.get(field)
				if not key_string:
					continue
				key = _extract_key_from_key_string(key_string)
				keys[key] = {
					"key_doctype": doctype,
					"key_document": document.name,
					"key_field": field,
				}
		return keys

	def parse_users(self, json_str):
		if not json_str:
			return []
		return json.loads(json_str)

	def is_system_manager_key(self, key) -> bool:
		key_info = self.known_keys.get(key, {})
		key_doctype = key_info.get("key_doctype")
		key_document = key_info.get("key_document")
		if not (key_doctype and key_document):
			return False
		document = frappe.get_doc(key_doctype, key_document)
		if not hasattr(document, "user"):
			return False
		if "System Manager" in frappe.get_roles(document.user):
			return True
		return False

	def check_key_violations(self):
		for host in self.hosts:
			for user in self.parse_users(host.users):
				for key in user["keys"]:
					if key in self.acceptable_keys:
						continue
					violation = {"host": host.host, "user": user["user"], "key": key}
					if key_info := self.known_keys.get(key):
						violation.update(key_info)
					if self.is_system_manager_key(key):
						self.append("known_violations", violation)
					else:
						self.append("violations", violation)

	def check_user_violations(self):
		suspicious_users = []
		acceptable_users = set(["frappe", "root"])
		for host in self.hosts:
			for user in self.parse_users(host.users):
				if user["user"] not in acceptable_users:
					suspicious_users.append((host.host, user["user"]))
		self.suspicious_users = json.dumps(suspicious_users, indent=1, sort_keys=True)

	def set_statistics(self):
		self.total_hosts = len(self.hosts)
		self.reachable_hosts = len([host for host in self.hosts if host.status == "Completed"])
		self.total_known_violations = len(self.known_violations)
		self.total_violations = len(self.violations)
		self.user_violations = len(json.loads(self.suspicious_users))

	def set_status(self):
		if self.violations or self.user_violations:
			self.status = "Failure"
		else:
			self.status = "Success"


class SSHAdHoc(AnsibleAdHoc):
	def _callback(self):
		return SSHCallback()

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

		return list(self.callback.hosts.values())


class SSHCallback(AnsibleCallback):
	def v2_runner_on_ok(self, result, *args, **kwargs):
		self.update_task("Completed", result)

	def v2_runner_on_failed(self, result, *args, **kwargs):
		self.update_task("Completed", result)

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
					"raw_keys": [],
				}
				for key in row["stdout_lines"]:
					stripped_key = key.strip()
					if stripped_key and not stripped_key.startswith("#"):
						user["raw_keys"].append(key)
						user["keys"].append(_extract_key_from_key_string(stripped_key))

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


def _extract_key_from_key_string(key_string):
	try:
		key_type, key, *_ = key_string.split()
		return f"{key_type} {key}"
	except Exception:
		return key_string


def run():
	audit = frappe.new_doc("SSH Access Audit")
	audit.insert()
	audit.run()
