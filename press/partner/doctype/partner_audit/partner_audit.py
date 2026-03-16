# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PartnerAudit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conducted_by: DF.Link | None
		date: DF.Date | None
		mode_of_audit: DF.Literal["", "Online", "In-Person", "Hybrid"]
		partner_audit_request: DF.Data | None
		partner_team: DF.Link | None
		result: DF.Literal["", "Compliant", "Non-Compliant"]
	# end: auto-generated types

	pass
