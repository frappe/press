# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe
from datetime import datetime
from press.utils.billing import convert_stripe_money
from press.telegram_utils import Telegram
from frappe.utils import get_url_to_form


EVENT_TYPE_MAP = {
	"invoice.finalized": "Finalized",
	"invoice.payment_succeeded": "Succeeded",
	"invoice.payment_failed": "Failed"
}

class StripeInvoiceWebhookHandler:
	"""This class handles Stripe Invoice Webhook Events"""

	events = [
		"invoice.payment_succeeded",
		"invoice.payment_failed",
		"invoice.finalized",
	]

	def __init__(self, webhook_log):
		self.webhook_log = webhook_log

	def process(self):
		if self.webhook_log.event_type not in self.events:
			return

		event = frappe.parse_json(self.webhook_log.payload)
		self.stripe_invoice = event["data"]["object"]
		self.invoice = frappe.get_doc(
			"Invoice", {"stripe_invoice_id": self.stripe_invoice["id"]}, for_update=True
		)
		self.team = frappe.get_doc("Team", self.invoice.team)
		event_type = self.webhook_log.event_type

		if event_type == "invoice.finalized":
			self.handle_finalized()
		elif event_type == "invoice.payment_succeeded":
			self.handle_payment_succeeded()
		elif event_type == "invoice.payment_failed":
			self.handle_payment_failed()

		payment_status = "Unpaid"
		if event_type == "invoice.payment_succeeded":
			payment_status = "Paid"
		elif event_type == "invoice.finalized" and self.stripe_invoice["status"] == "paid":
			payment_status = "Paid"
			

		frappe.get_doc({
			"doctype": "Stripe Payment Event",
			"invoice": self.invoice.name,
			"team": self.invoice.team,
			"event_type": EVENT_TYPE_MAP[event_type],
			"payment_status": payment_status
		}).insert()

	def handle_finalized(self):
		self.invoice.update(
			{
				"amount_paid": convert_stripe_money(self.stripe_invoice["amount_paid"]),
				"stripe_invoice_url": self.stripe_invoice["hosted_invoice_url"],
				"status": "Paid" if self.stripe_invoice["status"] == "paid" else "Unpaid",
			}
		)
		self.invoice.save()

	def handle_payment_succeeded(self):
		self.invoice.update(
			{
				"payment_date": datetime.fromtimestamp(
					self.stripe_invoice["status_transitions"]["paid_at"]
				),
				"status": "Paid",
				"amount_paid": self.stripe_invoice["amount_paid"] / 100,
				"stripe_invoice_url": self.stripe_invoice["hosted_invoice_url"],
			}
		)
		self.invoice.save()
		self.invoice.reload()

		# update transaction amount, fee and exchange rate
		if self.stripe_invoice.get("charge"):
			self.invoice.update_transaction_details(self.stripe_invoice.get("charge"))

		self.invoice.submit()

		# unsuspend sites
		self.team.unsuspend_sites(
			reason=f"Unsuspending sites because of successful payment of {self.invoice.name}"
		)

	def handle_payment_failed(self):
		attempt_date = self.stripe_invoice.get("webhooks_delivered_at")
		if attempt_date:
			attempt_date = datetime.fromtimestamp(attempt_date)
		attempt_count = self.stripe_invoice.get("attempt_count")
		self.invoice.update(
			{
				"payment_attempt_count": attempt_count,
				"payment_attempt_date": attempt_date,
				"status": "Unpaid",
			}
		)
		self.invoice.save()

		if self.team.free_account:
			return

		elif self.team.erpnext_partner:
			# dont suspend partner sites, send alert on telegram
			telegram = Telegram()
			team_url = get_url_to_form("Team", self.team.name)
			invoice_url = get_url_to_form("Invoice", self.invoice.name)
			telegram.send(
				f"Failed Invoice Payment [{self.invoice.name}]({invoice_url}) of"
				f" Partner: [{self.team.name}]({team_url})"
			)

			send_email_for_failed_payment(self.invoice)

		else:
			sites = None
			if attempt_count > 1:
				# suspend sites
				sites = self.team.suspend_sites(
					reason=f"Suspending sites because of failed payment of {self.invoice.name}"
				)
			send_email_for_failed_payment(self.invoice, sites)


def send_email_for_failed_payment(invoice, sites=None):
	team = frappe.get_doc("Team", invoice.team)
	email = team.user
	payment_method = team.default_payment_method
	last_4 = frappe.db.get_value("Stripe Payment Method", payment_method, "last_4")
	account_update_link = frappe.utils.get_url("/dashboard/welcome")
	subject = "Invoice Payment Failed for Frappe Cloud Subscription"

	frappe.sendmail(
		recipients=email,
		subject=subject,
		template="payment_failed_partner" if team.erpnext_partner else "payment_failed",
		args={
			"subject": subject,
			"payment_link": invoice.stripe_invoice_url,
			"amount": invoice.get_formatted("amount_due"),
			"account_update_link": account_update_link,
			"last_4": last_4 or "",
			"card_not_added": not payment_method,
			"sites": sites,
			"team": team,
		},
	)


def handle_stripe_invoice_webhook_events(doc, method):
	StripeInvoiceWebhookHandler(webhook_log=doc).process()
