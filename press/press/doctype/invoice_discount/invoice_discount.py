# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InvoiceDiscount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		based_on: DF.Literal["Percent", "Amount"]
		discount_type: DF.Literal["Flat On Total"]
		note: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		percent: DF.Percent
		via_items: DF.Check
		via_team: DF.Check
	# end: auto-generated types

	pass
