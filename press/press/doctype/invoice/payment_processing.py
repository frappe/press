# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

"""Track card payments that wait for the bank to confirm them, for example an
Indian card payment above the e-mandate limit that the customer must approve."""

import frappe
from frappe.utils import add_days, now_datetime

# Stripe confirms or fails a processing payment within this many days
PAYMENT_PROCESSING_DAYS = 14


def handle_payment_processing_webhook(doc, method):
	if doc.event_type != "payment_intent.processing":
		return
	payment_intent = frappe.parse_json(doc.payload)["data"]["object"]
	mark_invoice_payment_processing(payment_intent.get("invoice"))


def mark_invoice_payment_processing(stripe_invoice_id: str | None):
	if not stripe_invoice_id:
		return
	invoice = frappe.db.get_value(
		"Invoice", {"stripe_invoice_id": stripe_invoice_id, "status": ("!=", "Paid")}, "name"
	)
	if invoice:
		frappe.db.set_value("Invoice", invoice, "payment_processing_since", now_datetime())


def clear_stale_payment_processing():
	"""Clear the flag if Stripe never sent the result, so that the customer can pay again."""
	Invoice = frappe.qb.DocType("Invoice")
	(
		frappe.qb.update(Invoice)
		.set(Invoice.payment_processing_since, None)
		.where(Invoice.payment_processing_since < add_days(now_datetime(), -PAYMENT_PROCESSING_DAYS))
	).run()
