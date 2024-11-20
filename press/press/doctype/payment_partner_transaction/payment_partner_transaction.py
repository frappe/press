# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
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
	def on_submit(self):
		team = frappe.get_doc("Team", self.team)
		payment_partner_user = frappe.db.get_value("Team", self.payment_partner, "user")
		remark = f"Credit allocated via Payment Partner: {payment_partner_user} using {self.payment_gateway} gateway ({self.doctype} ID: {self.name})"
		team.allocate_credit_amount(self.amount, "Prepaid Credits", remark=remark)
