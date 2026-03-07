# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PartnerCertificateRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		course: DF.Data | None
		partner_member_email: DF.Link | None
		partner_member_name: DF.Data | None
		partner_team: DF.Link | None
	# end: auto-generated types

	def validate(self):
		if frappe.db.exists(
			"Partner Certificate Request",
			{
				"partner_team": self.partner_team,
				"partner_member_email": self.partner_member_email,
				"course": self.course,
			},
		):
			frappe.throw(
				f"Certificate Request already exists for user {self.partner_member_name} with course {'ERPNext' if self.course == 'erpnext-distribution' else 'Frappe Framework'}"
			)
