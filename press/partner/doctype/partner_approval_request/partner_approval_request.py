# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import get_url

from press.api.client import dashboard_whitelist


class PartnerApprovalRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approved_by_frappe: DF.Check
		approved_by_partner: DF.Check
		key: DF.Data | None
		partner: DF.Link | None
		requested_by: DF.Link | None
		send_mail: DF.Check
		status: DF.Literal["Pending", "Approved", "Rejected"]
	# end: auto-generated types

	dashboard_fields = (
		"requested_by",
		"partner",
		"status",
		"approved_by_frappe",
		"approved_by_partner",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		data = query.run(as_dict=True)
		for d in data:
			user = frappe.db.get_value("Team", d.requested_by, "user")
			d.update({"customer_email": user})
		return list(data)

	def before_insert(self):
		self.key = frappe.generate_hash(15)

	def before_save(self):
		if self.status == "Pending" and self.approved_by_partner and self.approved_by_frappe:
			self.status = "Approved"

			customer = frappe.get_doc("Team", self.requested_by)
			if not customer.partner_email:
				partner = frappe.get_doc("Team", self.partner)
				customer.partner_email = partner.partner_email
				customer.partnership_date = frappe.utils.getdate(self.creation)
				customer.save(ignore_permissions=True)

	@dashboard_whitelist()
	def approve_partner_request(self):
		if self.status == "Pending" and not self.approved_by_frappe:
			self.approved_by_partner = True
			self.save(ignore_permissions=True)
			self.reload()
			self.send_approval_request_email()

	def send_approval_request_email(self):
		from press.utils.billing import get_frappe_io_connection

		client = get_frappe_io_connection()
		email = frappe.db.get_value("Team", self.partner, "partner_email")
		partner_manager = client.get_value("Partner", "success_manager", {"email": email})
		if not partner_manager:
			frappe.throw("Failed to create approval request. Please contact support.")
		customer = frappe.db.get_value("Team", self.requested_by, "user")

		link = get_url(f"/api/method/press.api.partner.approve_partner_request?key={self.key}")

		frappe.sendmail(
			subject="Partner Approval Request",
			recipients=partner_manager["success_manager"],
			template="partner_approval",
			args={"link": link, "user": customer, "partner": email},
			now=True,
		)
