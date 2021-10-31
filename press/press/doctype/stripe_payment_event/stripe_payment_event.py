# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from datetime import datetime
from frappe.utils import get_url_to_form
from press.telegram_utils import Telegram
from frappe.model.document import Document
from press.utils.billing import convert_stripe_money, send_email_for_failed_payment

class StripePaymentEvent(Document):
	def after_insert(self):
		if self.event_type == "Finalized":
			self.handle_finalized()
		elif self.event_type == "Succeeded":
			self.handle_payment_succeeded()
		elif self.event_type == "Failed":
			self.handle_payment_failed()
	
	def handle_finalized(self):
		invoice = frappe.get_doc("Invoice", self.invoice, for_update=True)
		stripe_invoice = frappe.parse_json(self.stripe_invoice_object)

		invoice.update(
			{
				"amount_paid": convert_stripe_money(stripe_invoice["amount_paid"]),
				"stripe_invoice_url": stripe_invoice["hosted_invoice_url"],
				"status": self.payment_status,
			}
		)
		invoice.save()

	def handle_payment_succeeded(self):
		invoice = frappe.get_doc("Invoice", self.invoice, for_update=True)
		stripe_invoice = frappe.parse_json(self.stripe_invoice_object)
		team = frappe.get_doc("Team", self.team)

		invoice.update(
			{
				"payment_date": datetime.fromtimestamp(
					stripe_invoice["status_transitions"]["paid_at"]
				),
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

		# unsuspend sites
		team.unsuspend_sites(
			reason=f"Unsuspending sites because of successful payment of {self.invoice}"
		)

	def handle_payment_failed(self):
		invoice = frappe.get_doc("Invoice", self.invoice, for_update=True)
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
		self.suspend_sites_if_applicable(attempt_count)


	def suspend_sites_if_applicable(self, attempt_count):
		team = frappe.get_doc("Team", self.team)
		if team.free_account:
			return

		elif team.erpnext_partner:
			# dont suspend partner sites, send alert on telegram
			telegram = Telegram()
			team_url = get_url_to_form("Team", team.name)
			invoice_url = get_url_to_form("Invoice", self.invoice)
			telegram.send(
				f"Failed Invoice Payment [{self.invoice}]({invoice_url}) of"
				f" Partner: [{team.name}]({team_url})"
			)

			send_email_for_failed_payment(self.invoice)

		else:
			sites = None
			if attempt_count > 1:
				# suspend sites
				sites = team.suspend_sites(
					reason=f"Suspending sites because of failed payment of {self.invoice}"
				)
			send_email_for_failed_payment(self.invoice, sites)