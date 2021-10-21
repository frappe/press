# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe.model.document import Document


class MarketplaceAppSubscription(Document):
	def validate(self):
		self.validate_plan()

	def validate_plan(self):
		doctype_for_plan = frappe.db.get_value("Plan", self.plan, "document_type")

		if doctype_for_plan != "Marketplace App":
			frappe.throw(
				"Plan should be a Marketplace App document type plan, is"
				f" {doctype_for_plan} instead."
			)

	@frappe.whitelist()
	def activate(self):
		if self.status == "Active":
			frappe.throw("Subscription is already active.")
		
		self.status = "Active"
		self.save()