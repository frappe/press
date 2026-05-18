# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StaticIPLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		server: DF.DynamicLink
		server_type: DF.Link
		static_ip: DF.Data
		status: DF.Literal["Attached", "Detached"]
	# end: auto-generated types

	@property
	def provider(self):
		return frappe.db.get_value(self.server_type, self.server, "provider", cache=True)

	def validate(self):
		if self.server_type not in ("Server", "Database Server"):
			frappe.throw("Server Type must be either 'Server' or 'Database Server'")

	def after_insert(self):
		if self.status == "Attached":
			# TODO: check if any other server has the same static IP and if so, end subscription for that server and create new one for this server
			self._create_subscription()

		elif self.status == "Detached":
			# end subscription
			self._disable_subscription()

		frappe.throw("Invalid status. Status must be either 'Attached' or 'Detached'.")

	def _create_subscription(self):
		plan = frappe.get_value("Static IP Plan", {"provider": self.provider, "enabled": 1}, "name")
		if not plan:
			frappe.msgprint(f"No active Static IP Plan found for provider {self.provider}")
			return

		if frappe.db.exists(
			"Subscription",
			{
				"enabled": 1,
				"document_type": self.server_type,
				"document_name": self.server,
				"plan_type": "Static IP Plan",
				"plan": plan,
			},
		):
			return

		frappe.get_doc(
			{
				"doctype": "Subscription",
				"enabled": 1,
				"team": frappe.db.get_value(self.server_type, self.server, "team"),
				"document_type": self.server_type,
				"document_name": self.server,
				"plan_type": "Static IP Plan",
				"plan": plan,
				"interval": "Daily",
			}
		).insert(ignore_permissions=True)

	def _disable_subscription(self):
		frappe.db.set_value(
			"Subscription",
			{
				"enabled": 1,
				"document_type": self.server_type,
				"document_name": self.server,
				"plan_type": "Static IP Plan",
			},
			"enabled",
			0,
		)


def create_static_ip_log(server: str, server_type: str, static_ip: str, status: str = "Attached"):
	return frappe.get_doc(
		{
			"doctype": "Static IP Log",
			"server": server,
			"server_type": server_type,
			"static_ip": static_ip,
			"status": status,
		}
	).insert(ignore_permissions=True)
