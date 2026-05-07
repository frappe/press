# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IncidentBench(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Data
		current_sites_down: DF.Int
		last_seen_seconds_ago: DF.Duration | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reported_sites_down: DF.Int
	# end: auto-generated types

	pass
