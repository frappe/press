# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.api.billing import get_stripe
from press.utils.billing import get_frappe_io_connection
from press.utils import log_error
from datetime import datetime
from frappe import _
from frappe.utils import getdate, cint
from press.telegram import Telegram


class Invoice(Document):
	def validate(self):
		self.validate_team()
		self.validate_dates()
		self.validate_duplicate()
		self.validate_items()
		self.validate_amount()

	def before_submit(self):
		if self.type == "Prepaid Credits":
			return

		self.amount_due = self.total
		self.apply_credit_balance()
		if self.amount_due == 0:
			self.status = "Paid"

		self.update_item_descriptions()

		try:
			self.create_stripe_invoice()
		except Exception:
			frappe.db.rollback()

			msg = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
			self.add_comment("Comment", _("Submit Failed") + "<br><br>" + msg)
			frappe.db.commit()

			raise

	def after_submit(self):
		self.create_invoice_on_frappeio()

	def on_update_after_submit(self):
		self.create_invoice_on_frappeio()

	def after_insert(self):
		if self.get("amended_from"):
			values = {
				"modified": frappe.utils.now(),
				"modified_by": frappe.session.user,
				"new_invoice": self.name,
				"old_invoice": self.amended_from,
			}
			# link usage records of old cancelled invoice to the new amended invoice
			frappe.db.sql(
				"""
				UPDATE
					`tabUsage Record`
				SET
					`invoice` = %(new_invoice)s,
					`modified` = %(modified)s,
					`modified_by` = %(modified_by)s
				WHERE
					`invoice` = %(old_invoice)s
				""",
				values=values,
			)

	def create_stripe_invoice(self):
		if self.type == "Prepaid Credits":
			return
		if self.stripe_invoice_id:
			return
		if self.amount_due <= 0:
			return

		stripe = get_stripe()
		customer_id = frappe.db.get_value("Team", self.team, "stripe_customer_id")

		start = getdate(self.period_start)
		end = getdate(self.period_end)
		period_string = f"{start.strftime('%b %d')} - {end.strftime('%b %d')} {end.year}"
		stripe.InvoiceItem.create(
			customer=customer_id,
			description=f"Frappe Cloud Subscription ({period_string})",
			amount=int(self.amount_due * 100),
			currency=self.currency.lower(),
			idempotency_key=f"create_invoiceitem_{self.name}",
		)
		invoice = stripe.Invoice.create(
			customer=customer_id,
			collection_method="charge_automatically",
			auto_advance=True,
			idempotency_key=f"create_invoice_{self.name}",
		)
		self.db_set(
			{"stripe_invoice_id": invoice["id"], "status": "Invoice Created"}, commit=True
		)

	def finalize_stripe_invoice(self):
		stripe = get_stripe()
		stripe.Invoice.finalize_invoice(self.stripe_invoice_id)

	def validate_duplicate(self):
		if self.type == "Prepaid Credits":
			return

		if self.period_start and self.period_end and self.is_new():
			intersecting_invoices = frappe.db.sql(
				f"select `name` from `tabInvoice` where team = '{self.team}' and"
				f" docstatus < 2 and '{self.period_start}' between `period_start` and"
				f" `period_end` or '{self.period_end}' between `period_start` and"
				" `period_end`",
				as_list=True,
			)

			if intersecting_invoices:
				frappe.throw(
					"There are invoices with intersecting periods:"
					f" {', '.join(*intersecting_invoices)}",
					frappe.DuplicateEntryError,
				)

	def validate_team(self):
		self.customer_name = frappe.db.get_value(
			"Team", self.team, "billing_name"
		) or frappe.utils.get_fullname(self.team)
		self.customer_email = self.team
		self.currency = frappe.db.get_value("Team", self.team, "currency")
		if not self.currency:
			frappe.throw(
				f"Cannot create Invoice because Currency is not set in Team {self.team}"
			)

	def validate_dates(self):
		if not self.period_start:
			return
		if not self.period_end:
			period_start = getdate(self.period_start)
			# period ends on last day of month
			self.period_end = frappe.utils.get_last_day(period_start)

		# due date
		self.due_date = self.period_end

	def update_item_descriptions(self):
		for item in self.items:
			if item.document_type == "Site":
				site_name = item.document_name.split(".archived")[0]
				plan = frappe.get_cached_value("Plan", item.plan, "plan_title")
				how_many_days = f"{cint(item.quantity)} day{'s' if item.quantity > 1 else ''}"
				item.description = f"{site_name} active for {how_many_days} on {plan} plan"

	def add_usage_record(self, usage_record):
		if self.type != "Subscription":
			return
		# return if this usage_record is already accounted for in an invoice
		if usage_record.invoice:
			return

		# return if this usage_record does not fall inside period of invoice
		usage_record_date = getdate(usage_record.date)
		start = getdate(self.period_start)
		end = getdate(self.period_end)
		if not (start <= usage_record_date <= end):
			return

		invoice_item = self.get_invoice_item_for_usage_record(usage_record)
		# if not found, create a new invoice item
		if not invoice_item:
			invoice_item = self.append(
				"items",
				{
					"document_type": usage_record.document_type,
					"document_name": usage_record.document_name,
					"plan": usage_record.plan,
					"quantity": 0,
					"rate": usage_record.amount,
				},
			)

		invoice_item.quantity = (invoice_item.quantity or 0) + 1
		self.save()
		usage_record.db_set("invoice", self.name)

	def remove_usage_record(self, usage_record):
		if self.type != "Subscription":
			return
		# return if invoice is not in draft mode
		if self.docstatus != 0:
			return

		# return if this usage_record is of a different invoice
		if usage_record.invoice != self.name:
			return

		invoice_item = self.get_invoice_item_for_usage_record(usage_record)
		if not invoice_item:
			return

		if invoice_item.quantity <= 0:
			return

		invoice_item.quantity -= 1
		self.save()
		usage_record.db_set("invoice", None)

	def get_invoice_item_for_usage_record(self, usage_record):
		invoice_item = None
		for row in self.items:
			if (
				row.document_type == usage_record.document_type
				and row.document_name == usage_record.document_name
				and row.plan == usage_record.plan
				and row.rate == usage_record.amount
			):
				invoice_item = row
		return invoice_item

	def validate_items(self):
		for row in self.items:
			if row.quantity == 0:
				self.remove(row)
			else:
				row.amount = row.quantity * row.rate

	def validate_amount(self):
		total = 0
		for item in self.items:
			total += item.amount
		self.total = total

	def on_cancel(self):
		# make reverse entries for credit allocations
		for transaction in self.credit_allocations:
			doc = frappe.get_doc(
				doctype="Balance Transaction",
				team=self.team,
				type="Adjustment",
				source=transaction.source,
				currency=transaction.currency,
				amount=transaction.amount,
				description=f"Reversed on cancel of Invoice {self.name}",
			)
			doc.insert()
			doc.submit()

	def apply_credit_balance(self):
		balance = frappe.get_cached_doc("Team", self.team).get_balance()
		if balance == 0:
			return

		unallocated_balances = frappe.db.get_all(
			"Balance Transaction",
			filters={"team": self.team, "type": "Adjustment", "unallocated_amount": (">", 0)},
			fields=["name", "unallocated_amount", "source"],
			order_by="creation desc",
		)
		# sort by ascending for FIFO
		unallocated_balances.reverse()

		total_allocated = 0
		due = self.total
		for balance in unallocated_balances:
			if due == 0:
				break
			allocated = min(due, balance.unallocated_amount)
			due -= allocated
			self.append(
				"credit_allocations",
				{
					"transaction": balance.name,
					"amount": allocated,
					"currency": self.currency,
					"source": balance.source,
				},
			)
			doc = frappe.get_doc("Balance Transaction", balance.name)
			doc.append(
				"allocated_to",
				{"invoice": self.name, "amount": allocated, "currency": self.currency},
			)
			doc.save()
			total_allocated += allocated

		balance_transaction = frappe.get_doc(
			doctype="Balance Transaction",
			team=self.team,
			type="Applied To Invoice",
			amount=total_allocated * -1,
			invoice=self.name,
		).insert()
		balance_transaction.submit()

		self.applied_credits = total_allocated
		self.amount_due = self.total - self.applied_credits

	def create_next(self):
		# the next invoice's period starts after this invoice ends
		next_start = frappe.utils.add_days(self.period_end, 1)
		return frappe.get_doc(
			doctype="Invoice", team=self.team, period_start=next_start
		).insert()

	def get_pdf(self):
		print_format = self.meta.default_print_format
		return frappe.utils.get_url(
			f"/api/method/frappe.utils.print_format.download_pdf?doctype=Invoice&name={self.name}&format={print_format}&no_letterhead=0"
		)

	def create_invoice_on_frappeio(self):
		if self.flags.skip_frappe_invoice:
			return
		if self.status != "Paid":
			return
		if self.amount_due == 0:
			return
		if self.frappe_invoice:
			return

		try:
			client = self.get_frappeio_connection()
			response = client.session.post(
				f"{client.url}/api/method/create-fc-invoice",
				data={"invoice": frappe.as_json(self)},
			)
			if response.ok:
				res = response.json()
				invoice = res["message"]

				if invoice:
					self.frappe_invoice = invoice
					self.fetch_invoice_pdf()
					self.save()
					return invoice
			else:
				from bs4 import BeautifulSoup

				soup = BeautifulSoup(response.text, "html.parser")
				self.add_comment(
					text="Failed to create invoice on frappe.io" + "<br><br>" + str(soup.find("pre"))
				)
		except Exception:
			traceback = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
			self.add_comment(
				text="Failed to create invoice on frappe.io" + "<br><br>" + traceback
			)

	def fetch_invoice_pdf(self):
		if self.frappe_invoice:
			client = self.get_frappeio_connection()
			url = (
				client.url
				+ "/api/method/frappe.utils.print_format.download_pdf?"
				f"doctype=Sales%20Invoice&name={self.frappe_invoice}&"
				"format=Frappe%20Cloud&no_letterhead=0"
			)

			with client.session.get(url, stream=True) as r:
				r.raise_for_status()
				ret = frappe.get_doc(
					{
						"doctype": "File",
						"attached_to_doctype": "Invoice",
						"attached_to_name": self.name,
						"attached_to_field": "invoice_pdf",
						"folder": "Home/Attachments",
						"file_name": self.frappe_invoice + ".pdf",
						"is_private": 1,
						"content": r.content,
					}
				)
				ret.save(ignore_permissions=True)
				self.invoice_pdf = ret.file_url

	def get_frappeio_connection(self):
		if not hasattr(self, "frappeio_connection"):
			self.frappeio_connection = get_frappe_io_connection()

		return self.frappeio_connection

	def update_transaction_details(self, stripe_charge=None):
		if not stripe_charge:
			return
		stripe = get_stripe()
		charge = stripe.Charge.retrieve(stripe_charge)
		if charge.balance_transaction:
			balance_transaction = stripe.BalanceTransaction.retrieve(charge.balance_transaction)
			self.exchange_rate = balance_transaction.exchange_rate
			self.transaction_amount = convert_stripe_money(balance_transaction.amount)
			self.transaction_net = convert_stripe_money(balance_transaction.net)
			self.transaction_fee = convert_stripe_money(balance_transaction.fee)
			self.transaction_fee_details = []
			for row in balance_transaction.fee_details:
				self.append(
					"transaction_fee_details",
					{
						"description": row.description,
						"amount": convert_stripe_money(row.amount),
						"currency": row.currency.upper(),
					},
				)
			self.save()
			return True

	def refund(self, reason):
		stripe = get_stripe()
		charge = None
		if self.type == "Subscription":
			stripe_invoice = stripe.Invoice.retrieve(self.stripe_invoice_id)
			charge = stripe_invoice.charge
		elif self.type == "Prepaid Credits":
			payment_intent = stripe.PaymentIntent.retrieve(self.stripe_payment_intent_id)
			charge = payment_intent["charges"]["data"][0]["id"]

		if not charge:
			frappe.throw(
				"Cannot refund payment because Stripe Charge not found for this invoice"
			)

		stripe.Refund.create(charge=charge)
		self.status = "Refunded"
		self.save()
		self.add_comment(text=f"Refund reason: {reason}")

	def consume_credits_and_mark_as_paid(self, reason=None):
		if self.amount_due <= 0:
			frappe.throw("Amount due is less than or equal to 0")

		team = frappe.get_doc("Team", self.team)
		available_credits = team.get_balance()
		if available_credits < self.amount_due:
			available = frappe.utils.fmt_money(available_credits, 2, self.currency)
			frappe.throw(
				f"Available credits ({available}) is less than amount due"
				f" ({self.get_formatted('amount_due')})"
			)

		remark = "Manually consuming credits and marking the unpaid invoice as paid."
		if reason:
			remark += f" Reason: {reason}"

		self.change_stripe_invoice_status("Paid")

		# negative value to reduce balance by amount
		amount = self.amount_due * -1
		balance_transaction = team.allocate_credit_amount(
			amount, source="", remark=f"{remark}, Ref: Invoice {self.name}"
		)

		self.add_comment(
			text=(
				"Manually consuming credits and marking the unpaid invoice as paid."
				f" {frappe.utils.get_link_to_form('Balance Transaction', balance_transaction.name)}"
			)
		)
		self.db_set("status", "Paid")

	def change_stripe_invoice_status(self, status):
		stripe = get_stripe()
		if status == "Paid":
			stripe.Invoice.modify(self.stripe_invoice_id, paid=True)
		elif status == "Uncollectible":
			stripe.Invoice.mark_uncollectible(self.stripe_invoice_id)
		elif status == "Void":
			stripe.Invoice.void_invoice(self.stripe_invoice_id)


def submit_invoices():
	"""This method will run every day and submit the invoices whose period end was the previous day"""

	# get draft invoices whose period has ended before
	today = frappe.utils.today()
	invoices = frappe.db.get_all(
		"Invoice",
		{"status": "Draft", "period_end": ("<", today), "total": (">", 0)},
		pluck="name",
	)
	for name in invoices:
		invoice = frappe.get_doc("Invoice", name)
		submit_invoice(invoice)


def submit_invoice(invoice):
	try:
		invoice.submit()
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		log_error("Invoice Submit Failed", invoice=invoice.name)

	try:
		invoice.create_next()
	except Exception:
		frappe.db.rollback()
		log_error(
			"Invoice creation for next month failed", invoice=invoice.name,
		)


def process_stripe_webhook(doc, method):
	"""This method runs after a Stripe Webhook Log is created"""
	if doc.event_type not in [
		"invoice.payment_succeeded",
		"invoice.payment_failed",
		"invoice.finalized",
	]:
		return

	event = frappe.parse_json(doc.payload)
	stripe_invoice = event["data"]["object"]
	invoice = frappe.get_doc(
		"Invoice", {"stripe_invoice_id": stripe_invoice["id"]}, for_update=True
	)
	team = frappe.get_doc("Team", invoice.team)

	if doc.event_type == "invoice.finalized":
		invoice.update(
			{
				"amount_paid": stripe_invoice["amount_paid"] / 100,
				"stripe_invoice_url": stripe_invoice["hosted_invoice_url"],
				"status": "Paid" if stripe_invoice["status"] == "paid" else "Unpaid",
			}
		)
		invoice.save()

	elif doc.event_type == "invoice.payment_succeeded":
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

		# update transaction amount, fee and exchange rate
		if stripe_invoice.get("charge"):
			invoice.update_transaction_details(stripe_invoice.get("charge"))

		# unsuspend sites
		team.unsuspend_sites(
			reason=f"Unsuspending sites because of successful payment of {invoice.name}"
		)

	elif doc.event_type == "invoice.payment_failed":
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

		if team.erpnext_partner:
			# dont suspend partner sites, send alert on telegram
			telegram = Telegram()
			telegram.send(f"Failed Invoice Payment of Partner: {team.name}")
			send_email_for_failed_payment(invoice)
		else:
			sites = None
			if attempt_count > 1:
				# suspend sites
				sites = team.suspend_sites(
					reason=f"Suspending sites because of failed payment of {invoice.name}"
				)
			send_email_for_failed_payment(invoice, sites)


def convert_stripe_money(amount):
	return amount / 100


def send_email_for_failed_payment(invoice, sites=None):
	team = frappe.get_doc("Team", invoice.team)
	email = team.user
	payment_method = team.default_payment_method
	last_4 = frappe.db.get_value("Stripe Payment Method", payment_method, "last_4")
	account_update_link = frappe.utils.get_url("/dashboard/#/welcome")
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
