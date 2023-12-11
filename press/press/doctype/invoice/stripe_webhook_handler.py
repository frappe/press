# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe

from press.utils import log_error

EVENT_TYPE_MAP = {
	"invoice.finalized": "Finalized",
	"invoice.payment_succeeded": "Succeeded",
	"invoice.payment_failed": "Failed",
}

DISPUTE_EVENT_TYPE_MAP = {
	"charge.dispute.created": "Created",
	"charge.dispute.updated": "Updated",
	"charge.dispute.closed": "Closed",
}


class StripeWebhookHandler:
	"""This class handles Stripe Invoice Webhook Events"""

	def __init__(self, webhook_log):
		self.webhook_log = webhook_log

	def process(self):
		if self.webhook_log.event_type in DISPUTE_EVENT_TYPE_MAP.keys():
			event = frappe.parse_json(self.webhook_log.payload)
			id = event["data"]["object"]["id"]
			payment_intent = event["data"]["object"]["payment_intent"]
			email = event["data"]["object"]["evidence"]["customer_email_address"]

			try:
				frappe.get_doc(
					{
						"doctype": "Payment Dispute",
						"event_type": DISPUTE_EVENT_TYPE_MAP[self.webhook_log.event_type],
						"dispute_id": id,
						"payment_intent": payment_intent,
						"email": email,
					}
				).insert()
			except Exception:
				log_error("Stripe Payment Dispute Event Error", event=event)
				raise

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


def handle_stripe_webhook_events(doc, method):
	StripeWebhookHandler(webhook_log=doc).process()
