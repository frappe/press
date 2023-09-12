# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url


class PartnerApprovalRequest(Document):
	def before_insert(self):
		self.key = frappe.generate_hash(15)

	def after_insert(self):
		if self.send_mail:
			self.send_approval_request_email()

	def send_approval_request_email(self):
		email = frappe.db.get_value("Team", self.partner, "user")
		customer = frappe.db.get_value("Team", self.requested_by, "user")

		link = get_url(
			f"/api/method/press.api.account.approve_partner_request?key={self.key}"
		)

		frappe.sendmail(
			subject="Partner Approval Request",
			recipients=email,
			template="partner_approval",
			args={"link": link, "customer": customer},
			now=True,
		)
