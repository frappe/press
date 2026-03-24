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

		audit_date: DF.Date | None
		audit_report: DF.Attach | None
		conducted_by: DF.Link | None
		implementation_finding: DF.TextEditor | None
		implementation_observation: DF.TextEditor | None
		implementation_summary: DF.TextEditor | None
		mode_of_audit: DF.Literal["", "Online", "In-Person", "Hybrid"]
		next_actions: DF.TextEditor | None
		partner_team: DF.Link | None
		partner_tier: DF.Data | None
		proposed_audit_date: DF.Date | None
		requested_on: DF.Date | None
		sales_finding: DF.TextEditor | None
		sales_observation: DF.TextEditor | None
		sales_summary: DF.TextEditor | None
		status: DF.Literal["Requested", "Scheduled", "In Progress", "Completed", "On Hold", "Cancelled"]
		support_finding: DF.TextEditor | None
		support_observation: DF.TextEditor | None
		support_summary: DF.TextEditor | None
	# end: auto-generated types

	dashboard_fields = (
		"partner_team",
		"partner_tier",
		"mode_of_audit",
		"status",
		"audit_date",
		"conducted_by",
		"proposed_audit_date",
	)
