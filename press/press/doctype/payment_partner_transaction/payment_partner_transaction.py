# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PaymentPartnerTransaction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_amount: DF.Currency
		actual_currency: DF.Link | None
		amended_from: DF.Link | None
		amount: DF.Currency
		currency: DF.Link | None
		exchange_rate: DF.Float
		payment_gateway: DF.Link | None
		payment_partner: DF.Link | None
		payment_transaction_details: DF.Code | None
		posting_date: DF.Date | None
		submitted_to_frappe: DF.Check
		team: DF.Link | None
	# end: auto-generated types

	pass
