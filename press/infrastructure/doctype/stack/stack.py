# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Stack(Document):
	@frappe.whitelist()
	def deploy(self):
		deployment = frappe.new_doc("Deployment")
		deployment.stack = self.name
		deployment.insert()
