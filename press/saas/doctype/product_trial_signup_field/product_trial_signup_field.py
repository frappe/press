# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ProductTrialSignupField(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		fieldname: DF.Data
		fieldtype: DF.Literal["Data", "Select", "Check", "Date"]
		label: DF.Data
		options: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		required: DF.Check
	# end: auto-generated types

	pass
