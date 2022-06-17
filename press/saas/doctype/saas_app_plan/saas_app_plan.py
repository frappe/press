# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from typing import List
from frappe.model.document import Document


class SaasAppPlan(Document):
	def validate(self):
		self.validate_plan()
		self.validate_payout_percentage()

	def validate_plan(self):
		dt = frappe.db.get_value("Plan", self.plan, "document_type")

		if dt != "Saas App":
			frappe.throw("The plan must be a Saas App plan.")

	def validate_payout_percentage(self):
		if self.is_free:
			return

		site_plan = frappe.db.get_value("Plan", self.site_plan, "price_usd")
		saas_plan = frappe.db.get_value("Plan", self.plan, "price_usd")
		self.payout_percentage = 100 - float("{:.2f}".format((site_plan / saas_plan) * 100))


def get_app_plan_features(app_plan: str) -> List[str]:
	features = frappe.get_all(
		"Plan Feature", filters={"parent": app_plan}, pluck="description", order_by="idx"
	)

	return features
