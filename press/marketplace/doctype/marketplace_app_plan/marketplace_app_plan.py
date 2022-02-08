# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from typing import List
from frappe.model.document import Document


class MarketplaceAppPlan(Document):
	def validate(self):
		self.validate_plan()

	def validate_plan(self):
		dt = frappe.db.get_value("Plan", self.plan, "document_type")

		if dt != "Marketplace App":
			frappe.throw("The plan must be a Marketplace App plan.")


def get_app_plan_features(app_plan: str) -> List[str]:
	features = frappe.get_all(
		"Plan Feature", filters={"parent": app_plan}, pluck="description", order_by="idx"
	)

	return features
