# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PayoutOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		commission: DF.Currency
		currency: DF.Literal["USD", "INR"]
		document_name: DF.DynamicLink
		document_type: DF.Link
		gateway_fee: DF.Currency
		invoice: DF.Link
		invoice_item: DF.Link
		name: DF.Int | None
		net_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		plan: DF.Data | None
		quantity: DF.Float
		rate: DF.Currency
		site: DF.Link | None
		tax: DF.Currency
		total_amount: DF.Currency
	# end: auto-generated types

	pass
