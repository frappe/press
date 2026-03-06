# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IncidentPattern(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.incident_management.doctype.incident_pattern_investigation.incident_pattern_investigation import (
			IncidentPatternInvestigation,
		)

		causes: DF.Data
		investigations: DF.Table[IncidentPatternInvestigation]
		server: DF.DynamicLink | None
		server_type: DF.Link | None
	# end: auto-generated types
	pass
