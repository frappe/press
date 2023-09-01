# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PartnerApprovalRequest(Document):
	def after_insert(self):
		if self.send_email:
			self.send_approval_request_email()

	def send_approval_request_email():
		pass
