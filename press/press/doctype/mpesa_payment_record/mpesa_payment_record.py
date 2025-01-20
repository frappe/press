# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class MpesaPaymentRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount_usd: DF.Float
		balance_transaction: DF.Link | None
		bill_ref_number: DF.Data | None
		default_currency: DF.Data | None
		exchange_rate: DF.Float
		grand_total: DF.Currency
		invoice_number: DF.Data | None
		local_invoice: DF.SmallText | None
		merchant_request_id: DF.Data | None
		msisdn: DF.Data | None
		payment_partner: DF.Link | None
		posting_date: DF.Date | None
		posting_time: DF.Time | None
		team: DF.Link | None
		trans_amount: DF.Float
		trans_id: DF.Data | None
		trans_time: DF.Data | None
		transaction_type: DF.Literal["", "Mpesa Express", "Mpesa C2B"]
	# end: auto-generated types

	dashboard_fields = ("name", "posting_date", "trans_amount", "default_currency", "local_invoice")
