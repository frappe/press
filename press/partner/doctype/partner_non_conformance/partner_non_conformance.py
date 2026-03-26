# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PartnerNonConformance(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		audit_date: DF.Date | None
		auditor: DF.Link | None
		closed_by: DF.Link | None
		closed_on: DF.Date | None
		department: DF.Literal["General", "Implementation", "Support", "Sales"]
		evidence: DF.Attach | None
		expected_closure: DF.Date | None
		measures_to_close_nc: DF.Text | None
		nc_description: DF.Text | None
		nc_statement: DF.Data | None
		partner_audit: DF.Link | None
		partner_team: DF.Link | None
		status: DF.Literal["Open", "WIP", "Closed", "Discarded", "On Hold"]
	# end: auto-generated types

	dashboard_fields = (
		"name",
		"status",
		"department",
		"closed_by",
		"closed_on",
		"expected_closure",
		"measures_to_close_nc",
		"nc_description",
		"nc_statement",
		"auditor",
		"audit_date",
	)
