# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PartnerPaymentPayoutItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		amount_in_local_currency: DF.Currency
		commission_amount: DF.Currency
		exchange_rate: DF.Float
		net_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posting_date: DF.Date | None
		transaction_id: DF.Link
	# end: auto-generated types

	pass
