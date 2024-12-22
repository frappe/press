# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate
from frappe.utils.data import fmt_money

from press.api.billing import get_stripe
from press.api.client import dashboard_whitelist
from press.utils import log_error
from press.utils.billing import convert_stripe_money, get_frappe_io_connection


class Invoice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.invoice_credit_allocation.invoice_credit_allocation import (
			InvoiceCreditAllocation,
		)
		from press.press.doctype.invoice_discount.invoice_discount import InvoiceDiscount
		from press.press.doctype.invoice_item.invoice_item import InvoiceItem
		from press.press.doctype.invoice_transaction_fee.invoice_transaction_fee import InvoiceTransactionFee

		amended_from: DF.Link | None
		amount_due: DF.Currency
		amount_due_with_tax: DF.Currency
		amount_paid: DF.Currency
		applied_credits: DF.Currency
		billing_email: DF.Data | None
		credit_allocations: DF.Table[InvoiceCreditAllocation]
		currency: DF.Link | None
		customer_email: DF.Data | None
		customer_name: DF.Data | None
		customer_partnership_date: DF.Date | None
		discount_note: DF.Data | None
		discounts: DF.Table[InvoiceDiscount]
		due_date: DF.Date | None
		exchange_rate: DF.Float
		frappe_invoice: DF.Data | None
		frappe_partner_order: DF.Data | None
		frappe_partnership_date: DF.Date | None
		free_credits: DF.Currency
		gst: DF.Currency
		invoice_pdf: DF.Attach | None
		items: DF.Table[InvoiceItem]
		marketplace: DF.Check
		next_payment_attempt_date: DF.Date | None
		partner_email: DF.Data | None
		payment_attempt_count: DF.Int
		payment_attempt_date: DF.Date | None
		payment_date: DF.Date | None
		payment_mode: DF.Literal["", "Card", "Prepaid Credits", "NEFT", "Partner Credits", "Paid By Partner"]
		period_end: DF.Date | None
		period_start: DF.Date | None
		razorpay_order_id: DF.Data | None
		razorpay_payment_id: DF.Data | None
		razorpay_payment_method: DF.Data | None
		razorpay_payment_record: DF.Link | None
		refund_reason: DF.Data | None
		status: DF.Literal[
			"Draft", "Invoice Created", "Unpaid", "Paid", "Refunded", "Uncollectible", "Collected", "Empty"
		]
		stripe_invoice_id: DF.Data | None
		stripe_invoice_url: DF.Text | None
		stripe_payment_intent_id: DF.Data | None
		team: DF.Link
		total: DF.Currency
		total_before_discount: DF.Currency
		total_before_tax: DF.Currency
		total_discount_amount: DF.Currency
		transaction_amount: DF.Currency
		transaction_fee: DF.Currency
		transaction_fee_details: DF.Table[InvoiceTransactionFee]
		transaction_net: DF.Currency
		type: DF.Literal["Subscription", "Prepaid Credits", "Service", "Summary"]
		write_off_amount: DF.Float
	# end: auto-generated types

	dashboard_fields = (
		"period_start",
		"period_end",
		"team",
		"items",
		"currency",
		"type",
		"payment_mode",
		"total",
		"total_before_discount",
		"total_before_tax",
		"partner_email",
		"amount_due",
		"amount_paid",
		"docstatus",
		"gst",
		"applied_credits",
		"status",
		"due_date",
		"total_discount_amount",
		"invoice_pdf",
		"stripe_invoice_url",
		"amount_due_with_tax",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		StripeWebhookLog = frappe.qb.DocType("Stripe Webhook Log")
		Invoice = frappe.qb.DocType("Invoice")

		partner_customer = filters.get("partner_customer")
		if partner_customer:
			team_name = filters.get("team")
			due_date = filters.get("due_date")
			filters.pop("partner_customer")
			query = (
				frappe.qb.from_(Invoice)
				.select(Invoice.name, Invoice.total, Invoice.amount_due, Invoice.status, Invoice.due_date)
				.where(
					(Invoice.team == team_name)
					& (Invoice.due_date >= due_date[1])
					& (Invoice.type == "Subscription")
				)
			)

		invoices = (
			query.select(StripeWebhookLog.name.as_("stripe_payment_failed"))
			.left_join(StripeWebhookLog)
			.on(
				(Invoice.name == StripeWebhookLog.invoice)
				& (StripeWebhookLog.event_type == "payment_intent.payment_failed")
			)
			.groupby(Invoice.name)
		).run(as_dict=True)

		for invoice in invoices:
			if stripe_log := invoice.stripe_payment_failed:
				payload, failed_payment_method = frappe.db.get_value(
					"Stripe Webhook Log", stripe_log, ["payload", "stripe_payment_method"]
				)
				payload = frappe.parse_json(payload)
				invoice.stripe_payment_error = (
					payload.get("data", {}).get("object", {}).get("last_payment_error", {}).get("message")
				)
				invoice.stripe_payment_failed_card = frappe.db.get_value(
					"Stripe Payment Method", failed_payment_method, "last_4"
				)

		return invoices

	def get_doc(self, doc):
		doc.invoice_pdf = self.invoice_pdf or (self.currency == "USD" and self.get_pdf())
		currency = frappe.get_value("Team", self.team, "currency")
		price_field = "price_inr" if currency == "INR" else "price_usd"
		currency_symbol = "₹" if currency == "INR" else "$"

		for item in doc["items"]:
			if item.document_type in ("Server", "Database Server"):
				item.document_name = frappe.get_value(item.document_type, item.document_name, "title")
				if server_plan := frappe.get_value("Server Plan", item.plan, price_field):
					item.plan = f"{currency_symbol}{server_plan}"
				elif server_plan := frappe.get_value("Server Storage Plan", item.plan, price_field):
					item.plan = f"Storage Add-on {currency_symbol}{server_plan}/GB"
			elif item.document_type == "Marketplace App":
				item.document_name = frappe.get_value(item.document_type, item.document_name, "title")
				item.plan = (
					f"{currency_symbol}{frappe.get_value('Marketplace App Plan', item.plan, price_field)}"
				)

	@dashboard_whitelist()
	def stripe_payment_url(self):
		if not self.stripe_invoice_id:
			return
		frappe.response.location = self.get_stripe_payment_url()
		frappe.response.type = "redirect"

	def get_stripe_payment_url(self):
		stripe_link_expired = (
			self.status == "Unpaid" and frappe.utils.date_diff(frappe.utils.now(), self.due_date) > 30
		)
		if stripe_link_expired:
			stripe = get_stripe()
			stripe_invoice = stripe.Invoice.retrieve(self.stripe_invoice_id)
			url = stripe_invoice.hosted_invoice_url
		else:
			url = self.stripe_invoice_url
		return url

	def validate(self):
		self.validate_team()
		self.validate_dates()
		self.validate_duplicate()
		self.validate_items()
		self.calculate_values()
		self.compute_free_credits()

	def before_submit(self):
		if self.total > 0 and self.status != "Paid":
			frappe.throw("Invoice must be Paid to be submitted")

	def calculate_values(self):
		if self.status == "Paid" and self.docstatus == 1:
			# don't calculate if already invoice is paid and already submitted
			return
		self.calculate_total()
		self.calculate_discounts()
		self.calculate_amount_due()
		self.apply_taxes_if_applicable()

	@frappe.whitelist()
	def finalize_invoice(self):  # noqa: C901
		if self.type == "Prepaid Credits":
			return

		self.calculate_values()

		if self.total == 0:
			self.status = "Empty"
			self.submit()
			return

		team = frappe.get_doc("Team", self.team)
		if not team.enabled:
			self.add_comment("Info", "Skipping finalize invoice because team is disabled")
			self.save()
			return

		if self.stripe_invoice_id:
			# if stripe invoice is already created and paid,
			# then update status and return early
			stripe = get_stripe()
			invoice = stripe.Invoice.retrieve(self.stripe_invoice_id)
			if invoice.status == "paid":
				self.status = "Paid"
				self.update_transaction_details(invoice.charge)
				self.submit()
				self.unsuspend_sites_if_applicable()
				return

		# set as unpaid by default
		self.status = "Unpaid"
		self.update_item_descriptions()

		if self.amount_due > 0:
			self.apply_credit_balance()

		if self.amount_due == 0:
			self.status = "Paid"

		if self.status == "Paid" and self.stripe_invoice_id and self.amount_paid == 0:
			self.change_stripe_invoice_status("Void")
			self.add_comment(
				text=(
					f"Stripe Invoice {self.stripe_invoice_id} voided because" " payment is done via credits."
				)
			)

		self.save()

		if self.amount_due > 0:
			if self.payment_mode == "Prepaid Credits":
				self.add_comment(
					"Comment",
					"Not enough credits for this invoice. Change payment mode to Card to pay using Stripe.",
				)
			# we shouldn't depend on payment_mode to decide whether to create stripe invoice or not
			# there should be a separate field in team to decide whether to create automatic invoices or not
			if self.payment_mode == "Card":
				self.create_stripe_invoice()

		if self.status == "Paid":
			self.submit()
			self.unsuspend_sites_if_applicable()

	def unsuspend_sites_if_applicable(self):
		if (
			frappe.db.count(
				"Invoice",
				{
					"status": "Unpaid",
					"team": self.team,
					"type": "Subscription",
					"docstatus": ("<", 2),
				},
			)
			== 0
		):
			# unsuspend sites only if all invoices are paid
			team = frappe.get_cached_doc("Team", self.team)
			team.unsuspend_sites(f"Invoice {self.name} Payment Successful.")

	def calculate_total(self):
		total = 0
		for item in self.items:
			total += item.amount
		self.total = flt(total, 2)

	def apply_taxes_if_applicable(self):
		self.amount_due_with_tax = self.amount_due
		self.gst = 0

		if self.payment_mode == "Prepaid Credits":
			return

		if self.currency == "INR" and self.type == "Subscription":
			gst_rate = frappe.db.get_single_value("Press Settings", "gst_percentage")
			self.gst = flt(self.amount_due * gst_rate, 2)
			self.amount_due_with_tax = flt(self.amount_due + self.gst, 2)

	def calculate_amount_due(self):
		self.amount_due = flt(self.total - self.applied_credits, 2)
		if self.amount_due < 0 and self.amount_due > -0.1:
			self.write_off_amount = self.amount_due
			self.amount_due = 0

		if self.amount_due > 0 and self.amount_due < 0.1:
			self.write_off_amount = self.amount_due
			self.amount_due = 0

	def on_submit(self):
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
		if self.stripe_invoice_id:
			invoice = self.get_stripe_invoice()
			stripe_invoice_total = convert_stripe_money(invoice.total)
			if self.amount_due_with_tax == stripe_invoice_total:
				# return if an invoice with the same amount is already created
				return
			# if the amount is changed, void the stripe invoice and create a new one
			self.change_stripe_invoice_status("Void")
			formatted_amount = fmt_money(stripe_invoice_total, currency=self.currency)
			self.add_comment(
				text=(f"Stripe Invoice {self.stripe_invoice_id} of amount {formatted_amount} voided.")
			)
			self.stripe_invoice_id = ""
			self.stripe_invoice_url = ""
			self.save()

		if self.amount_due_with_tax <= 0:
			return

		customer_id = frappe.db.get_value("Team", self.team, "stripe_customer_id")
		amount = int(self.amount_due_with_tax * 100)
		self._make_stripe_invoice(customer_id, amount)

	def _make_stripe_invoice(self, customer_id, amount):
		mandate_id = self.get_mandate_id(customer_id)
		try:
			stripe = get_stripe()
			invoice = stripe.Invoice.create(
				customer=customer_id,
				pending_invoice_items_behavior="exclude",
				collection_method="charge_automatically",
				auto_advance=True,
				currency=self.currency.lower(),
				payment_settings={"default_mandate": mandate_id},
				idempotency_key=f"invoice:{self.name}:amount:{amount}",
			)
			stripe.InvoiceItem.create(
				customer=customer_id,
				invoice=invoice["id"],
				description=self.get_stripe_invoice_item_description(),
				amount=amount,
				currency=self.currency.lower(),
				idempotency_key=f"invoiceitem:{self.name}:amount:{amount}",
			)
			self.db_set(
				{
					"stripe_invoice_id": invoice["id"],
					"status": "Invoice Created",
				},
				commit=True,
			)
			self.reload()
			return invoice
		except Exception:
			frappe.db.rollback()
			self.reload()

			# log the traceback as comment
			msg = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
			self.add_comment("Comment", _("Stripe Invoice Creation Failed") + "<br><br>" + msg)
			frappe.db.commit()

	def get_mandate_id(self, customer_id):
		mandate_id = frappe.get_value(
			"Stripe Payment Method", {"team": self.team, "is_default": 1}, "stripe_mandate_id"
		)
		if not mandate_id:
			return ""
		return mandate_id

	def find_stripe_invoice_if_not_set(self):
		if self.stripe_invoice_id:
			return
		# if stripe invoice was created, find it and set it
		# so that we avoid scenarios where Stripe Invoice was created but not set in Frappe Cloud
		stripe = get_stripe()
		invoices = stripe.Invoice.list(customer=frappe.db.get_value("Team", self.team, "stripe_customer_id"))
		description = self.get_stripe_invoice_item_description()
		for invoice in invoices.data:
			line_items = invoice.lines.data
			if line_items and line_items[0].description == description and invoice.status != "void":
				self.stripe_invoice_id = invoice["id"]
				self.status = "Invoice Created"
				self.save()

	def get_stripe_invoice_item_description(self):
		start = getdate(self.period_start)
		end = getdate(self.period_end)
		period_string = f"{start.strftime('%b %d')} - {end.strftime('%b %d')} {end.year}"
		return f"Frappe Cloud Subscription ({period_string})"

	@frappe.whitelist()
	def finalize_stripe_invoice(self):
		stripe = get_stripe()
		stripe.Invoice.finalize_invoice(self.stripe_invoice_id)

	def validate_duplicate(self):
		invoice_exists = frappe.db.exists(
			"Invoice",
			{
				"stripe_payment_intent_id": self.stripe_payment_intent_id,
				"type": "Prepaid Credits",
				"name": ("!=", self.name),
			},
		)
		if self.type == "Prepaid Credits" and self.stripe_payment_intent_id and invoice_exists:
			frappe.throw("Invoice with same Stripe payment intent exists", frappe.DuplicateEntryError)

		if self.type == "Subscription" and self.period_start and self.period_end and self.is_new():
			query = (
				f"select `name` from `tabInvoice` where team = '{self.team}' and"
				f" status = 'Draft' and ('{self.period_start}' between `period_start` and"
				f" `period_end` or '{self.period_end}' between `period_start` and"
				" `period_end`)"
			)

			intersecting_invoices = [x[0] for x in frappe.db.sql(query, as_list=True)]

			if intersecting_invoices:
				frappe.throw(
					f"There are invoices with intersecting periods:{', '.join(intersecting_invoices)}",
					frappe.DuplicateEntryError,
				)

	def validate_team(self):
		team = frappe.get_doc("Team", self.team)

		self.customer_name = team.billing_name or frappe.utils.get_fullname(self.team)
		self.customer_email = (
			frappe.db.get_value("Communication Email", {"parent": team.user, "type": "invoices"}, ["value"])
			or team.user
		)
		self.currency = team.currency
		if not self.payment_mode:
			self.payment_mode = team.payment_mode
		if not self.currency:
			frappe.throw(f"Cannot create Invoice because Currency is not set in Team {self.team}")

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
			if not item.description:
				how_many_days = f"{cint(item.quantity)} day{'s' if item.quantity > 1 else ''}"
				if item.document_type == "Site" and item.plan:
					site_name = item.document_name.split(".archived")[0]
					plan = frappe.get_cached_value("Site Plan", item.plan, "plan_title")
					item.description = f"{site_name} active for {how_many_days} on {plan} plan"
				elif item.document_type in ["Server", "Database Server"]:
					server_title = frappe.get_cached_value(item.document_type, item.document_name, "title")
					if item.plan == "Add-on Storage plan":
						item.description = f"{server_title} Storage Add-on for {how_many_days}"
					else:
						item.description = f"{server_title} active for {how_many_days}"
				elif item.document_type == "Marketplace App":
					app_title = frappe.get_cached_value("Marketplace App", item.document_name, "title")
					item.description = f"Marketplace app {app_title} active for {how_many_days}"
				else:
					item.description = "Prepaid Credits"

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
					"site": usage_record.site,
				},
			)

		invoice_item.quantity = (invoice_item.quantity or 0) + 1

		if usage_record.payout:
			self.payout += usage_record.payout

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
			conditions = (
				row.document_type == usage_record.document_type
				and row.document_name == usage_record.document_name
				and row.plan == usage_record.plan
				and row.rate == usage_record.amount
			)
			if row.document_type == "Marketplace App":
				conditions = conditions and row.site == usage_record.site
			if conditions:
				invoice_item = row
		return invoice_item

	def validate_items(self):
		items_to_remove = []
		for row in self.items:
			if row.quantity == 0:
				items_to_remove.append(row)
			else:
				row.amount = flt((row.quantity * row.rate), 2)

		for item in items_to_remove:
			self.remove(item)

	def compute_free_credits(self):
		self.free_credits = sum([d.amount for d in self.credit_allocations if d.source == "Free Credits"])

	def apply_partner_discount(self):
		if self.flags.on_partner_conversion:
			return

		team = frappe.get_cached_doc("Team", self.team)
		partner_level, legacy_contract = team.get_partner_level()
		PartnerDiscounts = {"Entry": 0, "Bronze": 0.05, "Silver": 0.1, "Gold": 0.15}
		discount_percent = 0.1 if legacy_contract == 1 else PartnerDiscounts.get(partner_level)
		self.discount_note = "New Partner Discount"
		for item in self.items:
			if item.document_type in ("Site", "Server", "Database Server"):
				item.discount_percentage = discount_percent

	def calculate_discounts(self):
		for item in self.items:
			if item.discount_percentage:
				item.discount = flt(item.amount * (item.discount_percentage / 100), 2)

		self.total_discount_amount = sum([item.discount for item in self.items]) + sum(
			[d.amount for d in self.discounts]
		)
		# TODO: handle percent discount from discount table

		self.total_before_discount = self.total
		self.total = flt(self.total_before_discount - self.total_discount_amount, 2)

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
		# previously we used to cancel and re-apply credits, but it messed up the balance transaction history
		# so now we only do append-only operation while applying credits

		balance = frappe.get_cached_doc("Team", self.team).get_balance()
		if balance <= 0:
			return

		unallocated_balances = frappe.db.get_all(
			"Balance Transaction",
			filters={
				"team": self.team,
				"type": "Adjustment",
				"unallocated_amount": (">", 0),
				"docstatus": ("<", 2),
			},
			fields=["name", "unallocated_amount", "source"],
			order_by="creation desc",
		)
		# sort by ascending for FIFO
		unallocated_balances.reverse()

		total_allocated = 0
		due = self.amount_due
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

		self.applied_credits = sum(row.amount for row in self.credit_allocations)
		self.calculate_values()

	def create_next(self):
		# the next invoice's period starts after this invoice ends
		next_start = frappe.utils.add_days(self.period_end, 1)

		already_exists = frappe.db.exists(
			"Invoice",
			{
				"team": self.team,
				"period_start": next_start,
				"type": "Subscription",
			},  # Adding type 'Subscription' to ensure no other type messes with this
		)

		if already_exists:
			return None

		return frappe.get_doc(doctype="Invoice", team=self.team, period_start=next_start).insert()

	def get_pdf(self):
		print_format = self.meta.default_print_format
		return frappe.utils.get_url(
			f"/api/method/frappe.utils.print_format.download_pdf?doctype=Invoice&name={self.name}&format={print_format}&no_letterhead=0"
		)

	@frappe.whitelist()
	def create_invoice_on_frappeio(self):  # noqa: C901
		if self.flags.skip_frappe_invoice:
			return None
		if self.status != "Paid":
			return None
		if self.amount_paid == 0:
			return None
		if self.frappe_invoice or self.frappe_partner_order:
			return None

		try:
			team = frappe.get_doc("Team", self.team)
			address = frappe.get_doc("Address", team.billing_address) if team.billing_address else None
			if not address:
				# don't create invoice if address is not set
				return None
			client = self.get_frappeio_connection()
			response = client.session.post(
				f"{client.url}/api/method/create-fc-invoice",
				headers=client.headers,
				data={
					"team": team.as_json(),
					"address": address.as_json() if address else '""',
					"invoice": self.as_json(),
				},
			)
			if response.ok:
				res = response.json()
				invoice = res.get("message")

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

				log_error(
					"Frappe.io Invoice Creation Error",
					data={"invoice": self.name, "frappe_io_response": response.text},
				)
		except Exception:
			traceback = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
			self.add_comment(text="Failed to create invoice on frappe.io" + "<br><br>" + traceback)

			log_error(
				"Frappe.io Invoice Creation Error",
				data={"invoice": self.name, "traceback": traceback},
			)

	@frappe.whitelist()
	def fetch_invoice_pdf(self):
		if self.frappe_invoice:
			from urllib.parse import urlencode

			client = self.get_frappeio_connection()
			print_format = frappe.db.get_single_value("Press Settings", "print_format")
			params = urlencode(
				{
					"doctype": "Sales Invoice",
					"name": self.frappe_invoice,
					"format": print_format,
					"no_letterhead": 0,
				}
			)
			url = client.url + "/api/method/frappe.utils.print_format.download_pdf?" + params

			with client.session.get(url, headers=client.headers, stream=True) as r:
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

	def update_razorpay_transaction_details(self, payment):
		if not (payment["fee"] or payment["tax"]):
			return

		self.transaction_amount = convert_stripe_money(payment["amount"])
		self.transaction_net = convert_stripe_money(payment["amount"] - payment["fee"])
		self.transaction_fee = convert_stripe_money(payment["fee"])

		charges = [
			{
				"description": "GST",
				"amount": convert_stripe_money(payment["tax"]),
				"currency": payment["currency"],
			},
			{
				"description": "Razorpay Fee",
				"amount": convert_stripe_money(payment["fee"] - payment["tax"]),
				"currency": payment["currency"],
			},
		]

		for row in charges:
			self.append(
				"transaction_fee_details",
				{
					"description": row["description"],
					"amount": row["amount"],
					"currency": row["currency"].upper(),
				},
			)

		self.save()

	@frappe.whitelist()
	def refund(self, reason):
		stripe = get_stripe()
		charge = None
		if self.type in ["Subscription", "Service"]:
			stripe_invoice = stripe.Invoice.retrieve(self.stripe_invoice_id)
			charge = stripe_invoice.charge
		elif self.type == "Prepaid Credits":
			payment_intent = stripe.PaymentIntent.retrieve(self.stripe_payment_intent_id)
			charge = payment_intent["charges"]["data"][0]["id"]

		if not charge:
			frappe.throw("Cannot refund payment because Stripe Charge not found for this invoice")

		stripe.Refund.create(charge=charge)
		self.status = "Refunded"
		self.refund_reason = reason
		self.save()
		self.add_comment(text=f"Refund reason: {reason}")

	@frappe.whitelist()
	def change_stripe_invoice_status(self, status):
		stripe = get_stripe()
		if status == "Paid":
			stripe.Invoice.modify(self.stripe_invoice_id, paid=True)
		elif status == "Uncollectible":
			stripe.Invoice.mark_uncollectible(self.stripe_invoice_id)
		elif status == "Void":
			stripe.Invoice.void_invoice(self.stripe_invoice_id)

	@frappe.whitelist()
	def refresh_stripe_payment_link(self):
		stripe = get_stripe()
		stripe_invoice = stripe.Invoice.retrieve(self.stripe_invoice_id)
		self.stripe_invoice_url = stripe_invoice.hosted_invoice_url
		self.save()

		# Also send back the updated payment link
		return self.stripe_invoice_url

	def get_stripe_invoice(self):
		if not self.stripe_invoice_id:
			return None
		stripe = get_stripe()
		return stripe.Invoice.retrieve(self.stripe_invoice_id)


def finalize_draft_invoices():
	"""
	- Runs every hour
	- Processes 500 invoices at a time
	- Finalizes the invoices whose
	- period ends today and time is 6PM or later
	- period has ended before
	"""

	today = frappe.utils.today()
	# only finalize for enabled teams
	# since 'limit' returns the same set of invoices for disabled teams which are ignored
	enabled_teams = frappe.get_all("Team", {"enabled": 1}, pluck="name")

	# get draft invoices whose period has ended or ends today
	invoices = frappe.db.get_all(
		"Invoice",
		filters={
			"status": "Draft",
			"type": "Subscription",
			"period_end": ("<=", today),
			"team": ("in", enabled_teams),
		},
		pluck="name",
		limit=500,
		order_by="total desc",
	)

	current_time = frappe.utils.get_datetime().time()
	today = frappe.utils.getdate()
	for name in invoices:
		invoice = frappe.get_doc("Invoice", name)
		# don't finalize if invoice ends today and time is before 6 PM
		if invoice.period_end == today and current_time.hour < 18:
			continue
		finalize_draft_invoice(invoice)


def finalize_unpaid_prepaid_credit_invoices():
	"""Should be run daily in contrast to `finalize_draft_invoices`, which runs hourly"""
	today = frappe.utils.today()

	# Invoices with `Prepaid Credits` or `Partner Credits` as mode and unpaid
	invoices = frappe.db.get_all(
		"Invoice",
		filters={
			"status": "Unpaid",
			"type": "Subscription",
			"period_end": ("<=", today),
			"payment_mode": "Prepaid Credits",
		},
		pluck="name",
	)

	current_time = frappe.utils.get_datetime().time()
	today = frappe.utils.getdate()
	for name in invoices:
		invoice = frappe.get_doc("Invoice", name)
		# don't finalize if invoice ends today and time is before 6 PM
		if invoice.period_end == today and current_time.hour < 18:
			continue
		finalize_draft_invoice(invoice)


def finalize_draft_invoice(invoice):
	if isinstance(invoice, str):
		invoice = frappe.get_doc("Invoice", invoice)

	try:
		invoice.finalize_invoice()
	except Exception:
		frappe.db.rollback()
		msg = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
		invoice.add_comment(text="Finalize Invoice Failed" + "<br><br>" + msg)
	finally:
		frappe.db.commit()  # For the comment

	try:
		invoice.create_next()
	except Exception:
		frappe.db.rollback()
		log_error("Invoice creation for next month failed", invoice=invoice.name)


def calculate_gst(amount):
	return amount * 0.18


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabInvoice`.`team` = {frappe.db.escape(team)})"


def has_permission(doc, ptype, user):
	from press.utils import get_current_team, has_role

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return True

	if ptype == "create":
		return True

	if has_role("Press Support Agent", user) and ptype == "read":
		return True

	team = get_current_team(True)
	team_members = [
		d.user for d in frappe.db.get_all("Team Member", {"parenttype": "Team", "parent": doc.team}, ["user"])
	]
	if doc.team == team.name or team.user in team_members:
		return True
	return False
