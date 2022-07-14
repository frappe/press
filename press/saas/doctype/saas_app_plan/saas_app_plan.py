# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from typing import List
from frappe.model.document import Document
from press.press.doctype.invoice.invoice import calculate_gst
from press.utils import get_current_team


class SaasAppPlan(Document):
	def validate(self):
		self.validate_plan()
		self.validate_payout_percentage()

	def validate_plan(self):
		dt = frappe.db.get_value("Plan", self.plan, "document_type")

		if dt != "Saas App":
			frappe.throw("The plan must be a Saas App plan.")

	def get_total_amount(self, option):
		"""
		validates if plan is gst_inclusive, checks applicable country
		:option "Monthly" or "Annual"
		"""
		team = get_current_team(True)
		amount = frappe.db.get_value("Plan", self.plan, f"price_{team.currency.lower()}")
		amount = amount * 12 if option == "Annual" else amount

		if team.country == "India" and self.gst_inclusive:
			amount = amount + calculate_gst(amount)

		return amount

	def validate_payout_percentage(self):
		if self.is_free:
			return

		site_plan = frappe.db.get_value("Plan", self.site_plan, "price_usd")
		saas_plan = frappe.db.get_value("Plan", self.plan, "price_usd")
		self.payout_percentage = 100 - float("{:.2f}".format((site_plan / saas_plan) * 100))


def get_app_plan_features(app_plan: str) -> List[str]:
	return frappe.get_all(
		"Plan Feature", filters={"parent": app_plan}, pluck="description", order_by="idx"
	)
