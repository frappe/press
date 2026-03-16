# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PartnerAuditRequest(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		completed_on: DF.Date | None
		partner_team: DF.Link | None
		priority: DF.Literal["Low", "Medium", "High"]
		proposed_audit_date: DF.Date | None
		requested_on: DF.Date | None
		status: DF.Literal["Requested", "Scheduled", "In Progress", "Completed", "Oh Hold", "Cancelled"]
	# end: auto-generated types

	pass
