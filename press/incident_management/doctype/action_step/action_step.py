# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ActionStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_taken: DF.Check
		method: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
	# end: auto-generated types

	pass
