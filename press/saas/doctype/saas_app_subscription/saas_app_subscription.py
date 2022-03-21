# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SaasAppSubscription(Document):
	def validate(self):
		self.validate_saas_app_plan()
		self.set_plan()

	def before_insert(self):
		self.validate_duplicate_subscription()

	def validate_saas_app_plan(self):
		app = frappe.db.get_value("Saas App Plan", self.saas_app_plan, "app")

		if app != self.app:
			frappe.throw(f"Plan {self.saas_app_plan} is not for app {frappe.bold(self.app)}!")

	def set_plan(self):
		self.plan = frappe.db.get_value("Saas App Plan", self.saas_app_plan, "plan")

	def validate_duplicate_subscription(self):
		already_exists = frappe.db.exists(
			"Saas App Subscription", {"app": self.app, "site": self.site}
		)

		if already_exists:
			frappe.throw(
				f"Subscription for app '{frappe.bold(self.app)}' already exists for"
				f" site '{frappe.bold(self.site)}'!"
			)
