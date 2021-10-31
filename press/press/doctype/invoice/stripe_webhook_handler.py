# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

import frappe

from press.utils import log_error

EVENT_TYPE_MAP = {
	"invoice.finalized": "Finalized",
	"invoice.payment_succeeded": "Succeeded",
	"invoice.payment_failed": "Failed",
}


class StripeInvoiceWebhookHandler:
	"""This class handles Stripe Invoice Webhook Events"""

	def __init__(self, webhook_log):
		self.webhook_log = webhook_log

	def process(self):
		if self.webhook_log.event_type not in EVENT_TYPE_MAP.keys():
			return

		event = frappe.parse_json(self.webhook_log.payload)
		stripe_invoice = event["data"]["object"]
		self.invoice = frappe.get_doc("Invoice", {"stripe_invoice_id": stripe_invoice["id"]})

		event_type = self.webhook_log.event_type
		payment_status = "Unpaid"
		if event_type == "invoice.payment_succeeded":
			payment_status = "Paid"
		elif event_type == "invoice.finalized" and stripe_invoice["status"] == "paid":
			payment_status = "Paid"

		try:
			frappe.get_doc(
				{
					"doctype": "Stripe Payment Event",
					"invoice": self.invoice.name,
					"team": self.invoice.team,
					"event_type": EVENT_TYPE_MAP[event_type],
					"payment_status": payment_status,
					"stripe_invoice_object": frappe.as_json(stripe_invoice),
					"stripe_invoice_id": stripe_invoice["id"],
				}
			).insert()
		except Exception:
			log_error("Stripe Payment Event Error", event=event)
			raise


def handle_stripe_invoice_webhook_events(doc, method):
	StripeInvoiceWebhookHandler(webhook_log=doc).process()
