# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressJobStep(Document):
	@frappe.whitelist()
	def execute(self):
		self.status = "Running"
		self.save()

		job = frappe.get_doc("Press Job", self.job)
		if self.status == "Failure":
			job.fail()
		else:
			job.next()
