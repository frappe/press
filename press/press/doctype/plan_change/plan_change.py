# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class PlanChange(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		document_name: DF.DynamicLink
		document_type: DF.Link
		from_plan: DF.Link | None
		team: DF.Link | None
		timestamp: DF.Datetime | None
		to_plan: DF.Link
		type: DF.Literal["", "Initial Plan", "Upgrade", "Downgrade"]
	# end: auto-generated types

	def validate(self):
		self.team = frappe.db.get_value(self.document_type, self.document_name, "team")
		if self.from_plan and not self.type:
			from_plan_value = frappe.db.get_value("Server Plan", self.from_plan, "price_usd")
			to_plan_value = frappe.db.get_value("Server Plan", self.to_plan, "price_usd")
			self.type = "Downgrade" if from_plan_value > to_plan_value else "Upgrade"

		if self.type == "Initial Plan":
			self.from_plan = ""

	def after_insert(self):
		if self.type == "Initial Plan":
			self.create_subscription()
			return

		self.change_subscription_plan()

	def create_subscription(self):
		frappe.get_doc(
			doctype="Subscription",
			team=self.team,
			plan_type="Server Plan",
			plan=self.to_plan,
			document_type=self.document_type,
			document_name=self.document_name,
		).insert()

	def change_subscription_plan(self):
		document = frappe.get_doc(self.document_type, self.document_name)
		subscription = document.subscription
		if not subscription:
			frappe.throw(f"No subscription for {self.document_type} {self.document_name}")

		if self.from_plan and self.from_plan != subscription.plan:
			frappe.throw(
				_("{0} {1} is currently on {2} plan and not {3}").format(
					self.document_type, self.document_name, subscription.plan, self.from_plan
				)
			)

		subscription.plan = self.to_plan
		subscription.flags.updater_reference = {
			"doctype": self.doctype,
			"docname": self.name,
			"label": _("via Plan Change"),
		}
		subscription.enabled = 1
		subscription.save()
