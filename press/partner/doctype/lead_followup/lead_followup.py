# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class LeadFollowup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		communication_type: DF.Literal[
			"",
			"QFC",
			"DC",
			"Demo",
			"Phone call",
			"Email",
			"Online session",
			"Telecon",
			"WhatsApp",
			"Onsite visit",
		]
		date: DF.Date | None
		designation: DF.Data | None
		discussion: DF.SmallText | None
		followup_by: DF.Link | None
		no_show: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		spoke_to: DF.Data | None
	# end: auto-generated types

	pass
