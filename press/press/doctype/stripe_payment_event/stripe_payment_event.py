# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from datetime import datetime

import frappe
from frappe.model.document import Document

from press.api.billing import get_stripe
from press.utils.billing import convert_stripe_money


class StripePaymentEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event_type: DF.Literal["Finalized", "Failed", "Succeeded"]
		invoice: DF.Link | None
		payment_status: DF.Literal["Paid", "Unpaid"]
		stripe_invoice_id: DF.Data | None
		stripe_invoice_object: DF.Code | None
		team: DF.Link | None
	# end: auto-generated types

	def after_insert(self):
		if self.event_type == "Finalized":
			self.handle_finalized()
		elif self.event_type == "Succeeded":
			self.handle_payment_succeeded()
		elif self.event_type == "Failed":
			self.handle_payment_failed()

	def handle_finalized(self):
		invoice = frappe.get_doc("Invoice", self.invoice, for_update=True)
		if invoice.status == "Paid":
			return
		stripe_invoice = frappe.parse_json(self.stripe_invoice_object)

		invoice.update(
			{
				"amount_paid": convert_stripe_money(stripe_invoice["amount_paid"]),
				"stripe_invoice_url": stripe_invoice["hosted_invoice_url"],
				"status": self.payment_status,
				"stripe_payment_intent_id": stripe_invoice["payment_intent"],
			}
		)
		invoice.save()

	def handle_payment_succeeded(self):
		invoice = frappe.get_doc("Invoice", self.invoice, for_update=True)

		if invoice.status == "Paid" and invoice.amount_paid == 0:
			# check if invoice is already refunded
			stripe = get_stripe()
			inv = stripe.Invoice.retrieve(invoice.stripe_invoice_id)
			payment_intent = stripe.PaymentIntent.retrieve(inv.payment_intent)
			is_refunded = payment_intent["charges"]["data"][0]["refunded"]
			if is_refunded:
				return
			# if the fc invoice is already paid via credits and the stripe payment succeeded
			# issue a refund of the invoice payment
			invoice.refund(reason="Payment done via credits")
			invoice.add_comment(
				text=(
					f"Stripe Invoice {invoice.stripe_invoice_id} refunded because"
					" payment is done via credits and card both."
				)
			)
			return
		stripe_invoice = frappe.parse_json(self.stripe_invoice_object)
		team = frappe.get_doc("Team", self.team)

		invoice.update(
			{
				"payment_date": datetime.fromtimestamp(stripe_invoice["status_transitions"]["paid_at"]),
				"status": "Paid",
				"amount_paid": stripe_invoice["amount_paid"] / 100,
				"stripe_invoice_url": stripe_invoice["hosted_invoice_url"],
			}
		)
		invoice.save()
		invoice.reload()

		# update transaction amount, fee and exchange rate
		if stripe_invoice.get("charge"):
			invoice.update_transaction_details(stripe_invoice.get("charge"))

		invoice.submit()

		if (
			frappe.db.count(
				"Invoice",
				{
					"team": team.name,
					"status": "Unpaid",
					"type": "Subscription",
					"docstatus": ("<", 2),
				},
			)
			== 0
		):
			# unsuspend sites only if all invoices are paid
			team.unsuspend_sites(reason=f"Unsuspending sites because of successful payment of {self.invoice}")

	def handle_payment_failed(self):
		invoice = frappe.get_doc("Invoice", self.invoice, for_update=True)

		if invoice.status == "Paid":
			if invoice.amount_paid == 0:
				# check if invoice is already voided
				stripe = get_stripe()
				inv = stripe.Invoice.retrieve(invoice.stripe_invoice_id)
				if inv.status == "void":
					return
				# if the fc invoice is already paid via credits and the stripe payment failed
				# mark the stripe invoice as void
				invoice.change_stripe_invoice_status("Void")
				invoice.add_comment(
					text=(
						f"Stripe Invoice {invoice.stripe_invoice_id} voided because"
						" payment is done via credits."
					)
				)
			return

		stripe_invoice = frappe.parse_json(self.stripe_invoice_object)

		attempt_date = stripe_invoice.get("webhooks_delivered_at")
		if attempt_date:
			attempt_date = datetime.fromtimestamp(attempt_date)
		attempt_count = stripe_invoice.get("attempt_count")
		invoice.update(
			{
				"payment_attempt_count": attempt_count,
				"payment_attempt_date": attempt_date,
				"status": "Unpaid",
			}
		)
		invoice.save()
