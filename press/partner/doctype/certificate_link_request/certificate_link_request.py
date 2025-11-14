# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_url


class CertificateLinkRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		course: DF.Data | None
		key: DF.Data | None
		partner: DF.Data | None
		partner_team: DF.Link | None
		status: DF.Literal["Approved", "Pending"]
		user_email: DF.Link | None
	# end: auto-generated types

	def before_insert(self):
		self.status = "Pending"
		self.partner = frappe.db.get_value("Team", self.partner_team, "company_name")
		self.key = frappe.generate_hash(15)

	def after_save(self):
		if self.status == "Approved":
			certs = frappe.get_all(
				"Partner Certificate",
				filters={"partner_member_email": self.user_email, "course": self.course},
				pluck="name",
			)
			if certs:
				frappe.db.set_value("Partner Certificate", certs[0], "partner_team", self.partner_team)

	def after_insert(self):
		link = get_url(f"/api/method/press.api.partner.approve_certificate_link_request?key={self.key}")

		frappe.sendmail(
			recipients=[self.user_email],
			subject="Certificate Link Request",
			template="partner_link_certificate",
			args={"link": link, "partner": self.partner or "", "user": self.user_email},
			now=True,
		)
