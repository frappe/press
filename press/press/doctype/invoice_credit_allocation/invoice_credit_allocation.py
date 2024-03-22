# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


# import frappe
from frappe.model.document import Document


class InvoiceCreditAllocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		source: DF.Data | None
		transaction: DF.Link | None
	# end: auto-generated types

	pass
