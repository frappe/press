# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
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

	pass
