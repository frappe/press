# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.server_snapshot.server_snapshot import ServerSnapshot


class ServerSnapshotRecovery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.server_snapshot_site_recovery.server_snapshot_site_recovery import (
			ServerSnapshotSiteRecovery,
		)

		app_server: DF.Link | None
		app_server_archived: DF.Check
		database_server: DF.Link | None
		database_server_archived: DF.Check
		is_app_server_ready: DF.Check
		is_database_server_ready: DF.Check
		sites: DF.Table[ServerSnapshotSiteRecovery]
		snapshot: DF.Link
		status: DF.Literal["Draft", "Creating Servers", "Restoring", "Restored", "Failure"]
	# end: auto-generated types

	def before_insert(self):
		snapshot: ServerSnapshot = frappe.get_doc(
			"Server Snapshot",
			self.snapshot,
		)
		if snapshot.status != "Completed":
			frappe.throw(f"Cannot recover from snapshot {snapshot.name} with status {snapshot.status}")

	def on_update(self):
		if (
			self.status == "Creating Servers"
			and (
				self.has_value_changed("is_app_server_ready")
				or self.has_value_changed("is_database_server_ready")
			)
			and self.is_app_server_ready
			and self.is_database_server_ready
		):
			self.status = "Restoring"
			self.save()
			# self.restore_sites()

	@frappe.whitelist()
	def provision_servers(self):
		self.status = "Creating Servers"
		snapshot: ServerSnapshot = frappe.get_doc(
			"Server Snapshot",
			self.snapshot,
		)

		self.database_server = snapshot.create_server(
			server_type="Database Server", temporary_server=True, is_for_recovery=True
		)
		self.app_server = snapshot.create_server(
			server_type="Server",
			temporary_server=True,
			database_server=self.database_server,
			is_for_recovery=True,
		)
		self.save()

	@frappe.whitelist()
	def archive_servers(self):
		if not self.app_server or not self.database_server:
			frappe.throw("Servers are not provisioned yet.")

		app_server_doc = frappe.get_doc("Server", self.app_server)
		app_server_doc.archive()

		database_server_doc = frappe.get_doc("Database Server", self.database_server)
		database_server_doc.archive()

		self.save()

	def mark_server_provisioning_as_failed(self):
		self.status = "Failure"
		self.save()
