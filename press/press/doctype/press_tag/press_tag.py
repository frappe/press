# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PressTag(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		doctype_name: DF.Link | None
		tag: DF.Data | None
		team: DF.Link | None
	# end: auto-generated types

	dashboard_fields = ["tag", "doctype_name", "team"]
