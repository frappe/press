# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PartnerCertificate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		certificate_link: DF.Data | None
		course: DF.Data | None
		evaluator: DF.Data | None
		evaluator_name: DF.Data | None
		free: DF.Check
		issue_date: DF.Date | None
		partner_member_email: DF.Data | None
		partner_member_name: DF.Data | None
		team: DF.Link | None
		template: DF.Data | None
		version: DF.Data | None
	# end: auto-generated types

	dashboard_fields = (
		"certificate_link",
		"course",
		"version",
		"issue_date",
		"partner_member_name",
		"partner_member_email",
		"free",
	)
