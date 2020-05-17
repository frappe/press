# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime


class Payment(Document):
	def on_update(self):
		if self.status == "Failed":
			frappe.enqueue_doc(self.doctype, self.name, "suspend_sites")
		if self.status == "Paid":
			frappe.enqueue_doc(self.doctype, self.name, "unsuspend_sites")

	def on_submit(self):
		if self.status != "Paid":
			frappe.throw("Cannot submit if payment failed")

		doc = frappe.get_doc(
			{
				"doctype": "Payment Ledger Entry",
				"amount": self.amount,
				"purpose": "Payment",
				"team": self.team,
				"reference_doctype": "Payment",
				"reference_name": self.name,
			}
		)
		doc.insert()
		doc.submit()

	def suspend_sites(self):
		# suspend sites when payment failure occurs more than 1 time
		if self.attempt_count > 1:
			sites = frappe.get_doc("Team", self.team).suspend_sites(
				reason="Suspended because of payment failure"
			)
			self.send_email_for_failed_payment(sites)
		# send payment failure email when payment fails the first time
		else:
			self.send_email_for_failed_payment()

	def unsuspend_sites(self):
		frappe.get_doc("Team", self.team).unsuspend_sites(
			reason="Unsuspended on payment success"
		)

	def send_email_for_failed_payment(self, sites=None):
		team = frappe.get_doc("Team", self.team)
		email = team.user
		payment_method = team.default_payment_method
		last_4 = frappe.db.get_value("Stripe Payment Method", payment_method, "last_4")
		account_update_link = frappe.utils.get_url("/dashboard/#/welcome")

		frappe.sendmail(
			recipients=email,
			subject="Payment Failed for Frappe Cloud Subscription",
			template="payment_failed",
			args={
				"payment_link": self.payment_link,
				"amount": self.get_formatted("amount"),
				"account_update_link": account_update_link,
				"last_4": last_4 or "",
				"card_not_added": not payment_method,
				"sites": sites,
			},
		)


def process_stripe_webhook(doc, method):
	"""This method runs after a Stripe Webhook Log is created"""
	if doc.event_type not in ["invoice.payment_succeeded", "invoice.payment_failed"]:
		return

	event = frappe.parse_json(doc.payload)
	invoice = event["data"]["object"]
	customer_id = invoice["customer"]
	# value is in cents or paise
	amount = invoice["total"] / 100

	failed_payment = frappe.db.get_value(
		"Payment", {"status": "Failed", "stripe_invoice_id": invoice["id"]}
	)
	if failed_payment:
		payment = frappe.get_doc("Payment", failed_payment)
	else:
		team = frappe.db.get_value("Team", {"stripe_customer_id": customer_id}, "name")
		payment = frappe.get_doc(
			{
				"doctype": "Payment",
				"team": team,
				"amount": amount,
				"stripe_invoice_id": invoice["id"],
				"payment_link": invoice["hosted_invoice_url"],
			}
		)

	if doc.event_type == "invoice.payment_succeeded":
		payment.payment_date = datetime.fromtimestamp(
			invoice["status_transitions"]["paid_at"]
		)
		payment.status = "Paid"
		payment.save()
		payment.submit()
	elif doc.event_type == "invoice.payment_failed":
		payment.attempt_count = invoice.get("attempt_count")
		attempt_date = invoice.get("webhooks_delivered_at")
		if attempt_date:
			payment.attempt_date = datetime.fromtimestamp(attempt_date)
		payment.status = "Failed"
		payment.save()
