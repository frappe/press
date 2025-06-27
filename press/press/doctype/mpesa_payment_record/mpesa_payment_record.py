# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class MpesaPaymentRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Float
		amount_usd: DF.Float
		balance_transaction: DF.Link | None
		default_currency: DF.Data | None
		exchange_rate: DF.Float
		grand_total: DF.Currency
		invoice_number: DF.Data | None
		local_invoice: DF.SmallText | None
		merchant_request_id: DF.Data | None
		mpesa_receipt_number: DF.Data | None
		payment_partner: DF.Link | None
		phone_number: DF.Data | None
		posting_date: DF.Date | None
		posting_time: DF.Time | None
		team: DF.Link | None
		transaction_id: DF.Data | None
		transaction_time: DF.Datetime | None
		transaction_type: DF.Literal["", "Mpesa Express", "Mpesa C2B"]
	# end: auto-generated types

	dashboard_fields = (
		"name",
		"posting_date",
		"amount",
		"default_currency",
		"local_invoice",
		"amount_usd",
		"payment_partner",
		"exchange_rate",
		"grand_total",
	)

	def before_insert(self):
		self.validate_duplicate()

	def validate_duplicate(self):
		if frappe.db.exists(
			"Mpesa Payment Record",
			{"transaction_id": self.transaction_id, "docstatus": 1},
		):
			frappe.throw(f"Mpesa Payment Record for transaction {self.transaction_id} already exists")


def on_doctype_update():
	frappe.db.add_unique("Mpesa Payment Record", ["transaction_id"], constraint_name="unique_payment_record")
