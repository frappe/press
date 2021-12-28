# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document


class MarketplaceAppPlan(Document):
	def validate(self):
		self.validate_plan()

	def validate_plan(self):
		dt = frappe.db.get_value("Plan", self.plan, "document_type")

		if dt != "Marketplace App":
			frappe.throw("The plan must be a Marketplace App plan.")
