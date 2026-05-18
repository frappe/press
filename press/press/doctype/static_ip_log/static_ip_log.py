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

	def before_insert(self):
		if self.status == "Attached":
			self._check_if_can_enable_subscription()
		elif self.status == "Detached":
			self._check_if_can_disable_subscription()
		else:
			frappe.throw("Invalid status. Status must be either 'Attached' or 'Detached'.")

	def after_insert(self):
		if self.status == "Attached":
			self._create_subscription()
		elif self.status == "Detached":
			self._disable_subscription()

	def _get_plan(self):
		plan = frappe.db.get_value(
			"Static IP Plan", {"provider": self.provider, "enabled": 1}, "name", cache=True
		)
		if not plan:
			frappe.throw(f"No active Static IP Plan found for provider {self.provider}")
		return plan

	def _check_if_can_enable_subscription(self):
		if (
			last_status := frappe.db.get_value(
				"Static IP Log",
				{
					"static_ip": self.static_ip,
				},
				["status"],
				order_by="creation desc",
			)
		) and last_status == "Attached":
			# could be a case where the server wasn't synced properly
			frappe.throw(
				"Static IP seems to already be attached to a server. Please check the Static IP Logs."
			)

		if existing_sub := frappe.db.get_value(
			"Subscription",
			{
				"enabled": 1,
				"document_name": self.server,
				"plan_type": "Static IP Plan",
			},
			["plan", "name"],
			as_dict=True,
		):
			frappe.throw(
				f"Server already has an active subscription ({existing_sub.name}) for a Static IP Plan ({existing_sub.plan}). Please check the Subscriptions."
			)

	def _create_subscription(self):
		frappe.get_doc(
			{
				"doctype": "Subscription",
				"enabled": 1,
				"team": frappe.db.get_value(self.server_type, self.server, "team"),
				"document_type": self.server_type,
				"document_name": self.server,
				"plan_type": "Static IP Plan",
				"plan": self._get_plan(),
				"interval": "Daily",
			}
		).insert(ignore_permissions=True)

	def _check_if_can_disable_subscription(self):
		if (
			last_status := frappe.db.get_value(
				"Static IP Log",
				{
					"server": self.server,
					"static_ip": self.static_ip,
				},
				["status"],
				order_by="creation desc",
			)
		) and last_status == "Detached":
			frappe.throw(
				"Static IP seems to already be detached from the server. Please check the Static IP Logs."
			)

	def _disable_subscription(self):
		if not (
			sub := frappe.db.get_value(
				"Subscription",
				{
					"enabled": 1,
					"document_type": self.server_type,
					"document_name": self.server,
					"plan_type": "Static IP Plan",
				},
				"name",
			)
		):
			frappe.throw(f"No active Static IP subscription found for {self.server_type} {self.server}.")

		frappe.db.set_value("Subscription", sub, "enabled", 0)


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
