# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from datetime import datetime
from frappe.model.document import Document
from press.utils.billing import get_razorpay_client


class RazorpayPaymentRecord(Document):
	def on_update(self):
		if self.has_value_changed("status") and self.status == "Captured":
			self.process_prepaid_credits()

	def process_prepaid_credits(self):
		team = frappe.get_doc("Team", self.team)

		client = get_razorpay_client()
		payment = client.payment.fetch(self.payment_id)
		amount = payment["amount"] / 100
		balance_transaction = team.allocate_credit_amount(
			amount, source="Prepaid Credits", remark=f"Razorpay: {self.payment_id}"
		)

		# Add a field to track razorpay event
		invoice = frappe.get_doc(
			doctype="Invoice",
			team=team.name,
			type="Prepaid Credits",
			status="Paid",
			due_date=datetime.fromtimestamp(payment["created_at"]),
			amount_paid=amount,
			amount_due=amount,
			razorpay_order_id=self.order_id,
			razorpay_payment_record=self.name,
			razorpay_payment_method=payment["method"],
		)
		invoice.append(
			"items",
			{
				"description": "Prepaid Credits",
				"document_type": "Balance Transaction",
				"document_name": balance_transaction.name,
				"quantity": 1,
				"rate": amount,
			},
		)
		invoice.insert()
		invoice.reload()

		invoice.update_razorpay_transaction_details(payment)
		invoice.submit()
