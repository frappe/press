# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class InvoiceItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		description: DF.Data | None
		discount: DF.Currency
		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		has_marketplace_payout_completed: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		plan: DF.Data | None
		quantity: DF.Float
		rate: DF.Currency
		site: DF.Link | None
	# end: auto-generated types

	pass
