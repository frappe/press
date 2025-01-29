# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class SSHAccessAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.ssh_access_audit_command.ssh_access_audit_command import (
			SSHAccessAuditCommand,
		)
		from press.infrastructure.doctype.ssh_access_audit_violation.ssh_access_audit_violation import (
			SSHAccessAuditViolation,
		)

		commands: DF.Table[SSHAccessAuditCommand]
		inventory: DF.Code | None
		name: DF.Int | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		violations: DF.Table[SSHAccessAuditViolation]
	# end: auto-generated types

	def before_insert(self):
		self.set_inventory()

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
