# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Stack(Document):
	def validate(self):
		if not self.vxlan_id:
			# Use the last 3 bytes of the name as the VXLAN ID
			self.vxlan_id = int(self.name[-6:], 16)

	@frappe.whitelist()
	def deploy(self):
		deployment = frappe.new_doc("Deployment")
		deployment.stack = self.name
		deployment.insert()
