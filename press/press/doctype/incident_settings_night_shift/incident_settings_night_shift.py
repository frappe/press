# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IncidentSettingsNightShift(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		day: DF.Literal["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		user: DF.Link
	# end: auto-generated types

	pass
