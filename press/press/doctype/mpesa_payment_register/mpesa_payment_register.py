# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MpesaPaymentRegister(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		bill_ref_number: DF.Data | None
		company: DF.Link | None
		default_currency: DF.Data | None
		invoice_number: DF.Data | None
		merchant_request_id: DF.Data | None
		msisdn: DF.Data | None
		org_account_balance: DF.Data | None
		payment_partner: DF.Data | None
		posting_date: DF.Date | None
		posting_time: DF.Time | None
		submit_payment: DF.Check
		third_party_transid: DF.Data | None
		trans_amount: DF.Float
		trans_id: DF.Data | None
		trans_time: DF.Data | None
		transaction_type: DF.Literal["", "Mpesa Express", "Mpesa C2B"]
	# end: auto-generated types
	pass
