# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe

from frappe import _
from enum import Enum
from press.utils import log_error
from frappe.core.utils import find_all
from frappe.utils import getdate, cint
from frappe.utils.data import fmt_money
from press.api.billing import get_stripe
from frappe.model.document import Document

from press.overrides import get_permission_query_conditions_for_doctype
from press.utils.billing import get_frappe_io_connection, convert_stripe_money


class InvoiceDiscountType(Enum):
	FLAT_ON_TOTAL = "Flat On Total"


discount_type_string_to_enum = {"Flat On Total": InvoiceDiscountType.FLAT_ON_TOTAL}


class Invoice(Document):
	def validate(self):
		self.validate_team()
		self.validate_dates()
		self.validate_duplicate()
		self.validate_items()
		self.validate_amount()
		self.compute_free_credits()
		self.validate_gst()

	def before_submit(self):
		if self.total > 0 and self.status != "Paid":
			frappe.throw("Invoice must be Paid to be submitted")

	@frappe.whitelist()
	def finalize_invoice(self):
		if self.type == "Prepaid Credits":
			return

		if self.total == 0:
			self.status = "Empty"
			self.submit()
			return

		team_enabled = frappe.db.get_value("Team", self.team, "enabled")
		if not team_enabled:
			self.add_comment("Info", "Skipping finalize invoice because team is disabled")
			return

		# set as unpaid by default
		self.status = "Unpaid"

		self.amount_due = self.total

		if self.payment_mode == "Partner Credits":
			self.payment_attempt_count += 1
			self.save()
			frappe.db.commit()

			self.cancel_applied_credits()
			self.apply_partner_credits()
			return

		self.apply_credit_balance()
		if self.amount_due == 0:
			self.status = "Paid"

		self.update_item_descriptions()

		if self.payment_mode == "Prepaid Credits" and self.amount_due > 0:
			self.payment_attempt_count += 1
			self.save()
			frappe.db.commit()

			frappe.throw(
				"Not enough credits for this invoice. Change payment mode to Card to"
				" pay using Stripe."
			)

		try:
			self.create_stripe_invoice()
		except Exception:
			frappe.db.rollback()
			self.reload()

			# log the traceback as comment
			msg = "<pre><code>" + frappe.get_traceback() + "</pre></code>"
			self.add_comment("Comment", _("Stripe Invoice Creation Failed") + "<br><br>" + msg)

			if not self.stripe_invoice_id:
				# if stripe invoice was created, find it and set it
				# so that we avoid scenarios where Stripe Invoice was created but not set in Frappe Cloud
				stripe_invoice_id = self.find_stripe_invoice()
				if stripe_invoice_id:
					self.stripe_invoice_id = stripe_invoice_id
					self.status = "Invoice Created"
					self.save()

			frappe.db.commit()

			raise

		self.save()

		if self.status == "Paid":
			self.submit()

			team = frappe.get_cached_doc("Team", self.team)
			team.unsuspend_sites(f"Invoice {self.name} Payment Successful.")

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
		if self.payment_mode != "Card":
			return

		stripe = get_stripe()

		if self.type == "Prepaid Credits":
			return

		if self.status == "Paid":
			# void an existing invoice if payment was done via credits
			if self.stripe_invoice_id:
				stripe.Invoice.void_invoice(self.stripe_invoice_id)
				self.add_comment(
					text=(
						f"Stripe Invoice {self.stripe_invoice_id} voided because"
						" payment is done via credits."
					)
				)
			return

		if self.stripe_invoice_id:
			invoice = stripe.Invoice.retrieve(self.stripe_invoice_id)
			stripe_invoice_total = convert_stripe_money(invoice.total)
			if self.amount_due == stripe_invoice_total:
				# return if an invoice with the same amount is already created
				return
			else:
				# if the amount is changed, void the stripe invoice and create a new one
				stripe.Invoice.void_invoice(self.stripe_invoice_id)
				formatted_amount = fmt_money(stripe_invoice_total, currency=self.currency)
				self.add_comment(
					text=(
						f"Stripe Invoice {self.stripe_invoice_id} of amount {formatted_amount} voided."
					)
				)
				self.stripe_invoice_id = ""
				self.stripe_invoice_url = ""

		if self.amount_due <= 0:
			return

		customer_id = frappe.db.get_value("Team", self.team, "stripe_customer_id")
		amount = int(self.amount_due * 100)
		stripe.InvoiceItem.create(
			customer=customer_id,
			description=self.get_stripe_invoice_item_description(),
			amount=amount,
			currency=self.currency.lower(),
			idempotency_key=f"invoiceitem:{self.name}:{amount}",
		)
		invoice = stripe.Invoice.create(
			customer=customer_id,
			collection_method="charge_automatically",
			auto_advance=True,
			idempotency_key=f"invoice:{self.name}:{amount}",
		)
		self.stripe_invoice_id = invoice["id"]
		self.status = "Invoice Created"
		self.save()

	def find_stripe_invoice(self):
		stripe = get_stripe()
		invoices = stripe.Invoice.list(
			customer=frappe.db.get_value("Team", self.team, "stripe_customer_id")
		)
		description = self.get_stripe_invoice_item_description()
		for invoice in invoices.data:
			if invoice.lines.data[0].description == description and invoice.status != "void":
				return invoice["id"]

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
		if self.type != "Subscription":
			return

		if self.period_start and self.period_end and self.is_new():
			query = (
				f"select `name` from `tabInvoice` where team = '{self.team}' and"
				f" docstatus < 2 and ('{self.period_start}' between `period_start` and"
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
		team = frappe.get_cached_doc("Team", self.team)

		self.customer_name = team.billing_name or frappe.utils.get_fullname(self.team)
		self.customer_email = (
			frappe.db.get_value(
				"Communication Email", {"parent": self.team, "type": "invoices"}, ["value"]
			)
			or self.team
		)
		self.currency = team.currency
		if not self.payment_mode:
			self.payment_mode = team.payment_mode
		if not self.currency:
			frappe.throw(
				f"Cannot create Invoice because Currency is not set in Team {self.team}"
			)

		# To prevent copying of team level discounts again
		self.remove_previous_team_discounts()

		for invoice_discount in team.discounts:
			self.append(
				"discounts",
				{
					"discount_type": invoice_discount.discount_type,
					"based_on": invoice_discount.based_on,
					"percent": invoice_discount.percent,
					"amount": invoice_discount.amount,
					"via_team": True,
				},
			)

	def validate_gst(self):
		if self.gst_inclusive:
			self.gst = calculate_gst(self.total)

	def remove_previous_team_discounts(self):
		team_discounts = find_all(self.discounts, lambda x: x.via_team)

		for discount in team_discounts:
			self.remove(discount)

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
			if not item.description and item.document_type == "Site" and item.plan:
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
			if (
				row.document_type == usage_record.document_type
				and row.document_name == usage_record.document_name
				and row.plan == usage_record.plan
				and row.rate == usage_record.amount
			):
				invoice_item = row
		return invoice_item

	def validate_items(self):
		items_to_remove = []
		for row in self.items:
			if row.quantity == 0:
				items_to_remove.append(row)
			else:
				row.amount = row.quantity * row.rate

		for item in items_to_remove:
			self.remove(item)

	def validate_amount(self):
		# Already Submitted
		if self.docstatus == 1:
			return

		total = 0
		for item in self.items:
			total += item.amount

		self.total_before_discount = total
		self.set_total_and_discount()

	def compute_free_credits(self):
		self.free_credits = sum(
			[d.amount for d in self.credit_allocations if d.source == "Free Credits"]
		)

	def set_total_and_discount(self):
		total_discount_amount = 0

		for invoice_discount in self.discounts:
			discount_type = discount_type_string_to_enum[invoice_discount.discount_type]
			if discount_type == InvoiceDiscountType.FLAT_ON_TOTAL:
				total_discount_amount += self.get_flat_on_total_discount_amount(invoice_discount)

		self.total_discount_amount = total_discount_amount
		self.total = self.total_before_discount - total_discount_amount

	def get_flat_on_total_discount_amount(self, invoice_discount):
		discount_amount = 0

		if invoice_discount.based_on == "Amount":
			if invoice_discount.amount > self.total_before_discount:
				frappe.throw(
					f"Discount amount {invoice_discount.amount} cannot be"
					f" greater than total amount {self.total_before_discount}"
				)

			discount_amount = invoice_discount.amount
		elif invoice_discount.based_on == "Percent":
			if invoice_discount.percent > 100:
				frappe.throw(
					f"Discount percentage {invoice_discount.percent} cannot be greater than 100%"
				)
			discount_amount = self.total_before_discount * (invoice_discount.percent / 100)

		return discount_amount

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

	def apply_partner_credits(self):
		client = self.get_frappeio_connection()
		response = client.session.post(
			f"{client.url}/api/method/consume_credits_against_fc_invoice",
			headers=client.headers,
			data={"invoice": self.as_json()},
		)

		if response.ok:
			res = response.json()
			partner_order = res.get("message")

			if partner_order:
				self.frappe_partner_order = partner_order
				self.amount_paid = self.amount_due
				self.status = "Paid"
				self.save()
				self.submit()
		else:
			self.add_comment(
				text="Failed to pay via Partner credits" + "<br><br>" + response.text
			)

	def apply_credit_balance(self):
		# cancel applied credits to re-apply available credits
		self.cancel_applied_credits()

		balance = frappe.get_cached_doc("Team", self.team).get_balance()
		if balance <= 0:
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

	def cancel_applied_credits(self):
		for row in self.credit_allocations:
			doc = frappe.get_doc(
				doctype="Balance Transaction",
				type="Adjustment",
				source=row.source,
				team=self.team,
				amount=row.amount,
				description=(
					f"Reverse amount {row.get_formatted('amount')} of {row.transaction}"
					f" from invoice {self.name}"
				),
			).insert()
			doc.submit()
			self.applied_credits -= row.amount

		self.clear_credit_allocation_table()
		self.save()

	def clear_credit_allocation_table(self):
		self.set("credit_allocations", [])

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

		if not already_exists:
			return frappe.get_doc(
				doctype="Invoice", team=self.team, period_start=next_start
			).insert()

	def get_pdf(self):
		print_format = self.meta.default_print_format
		return frappe.utils.get_url(
			f"/api/method/frappe.utils.print_format.download_pdf?doctype=Invoice&name={self.name}&format={print_format}&no_letterhead=0"
		)

	@frappe.whitelist()
	def create_invoice_on_frappeio(self):
		if self.flags.skip_frappe_invoice:
			return
		if self.status != "Paid":
			return
		if self.amount_paid == 0:
			return
		if self.frappe_invoice or self.frappe_partner_order:
			return

		try:
			team = frappe.get_doc("Team", self.team)
			address = (
				frappe.get_doc("Address", team.billing_address) if team.billing_address else None
			)
			client = self.get_frappeio_connection()
			response = client.session.post(
				f"{client.url}/api/method/create-fc-invoice",
				headers=client.headers,
				data={
					"team": team.as_json(),
					"address": address.as_json(),
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
			self.add_comment(
				text="Failed to create invoice on frappe.io" + "<br><br>" + traceback
			)

			log_error(
				"Frappe.io Invoice Creation Error",
				data={"invoice": self.name, "traceback": traceback},
			)

	@frappe.whitelist()
	def fetch_invoice_pdf(self):
		if self.frappe_invoice:
			client = self.get_frappeio_connection()
			url = (
				client.url + "/api/method/frappe.utils.print_format.download_pdf?"
				f"doctype=Sales%20Invoice&name={self.frappe_invoice}&"
				"format=Frappe%20Cloud&no_letterhead=0"
			)

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
			return True

	def update_razorpay_transaction_details(self, payment):
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


def finalize_draft_invoices():
	"""
	- Runs every hour
	- Processes 500 invoices at a time
	- Finalizes the invoices whose
	- period ends today and time is 6PM or later
	- period has ended before
	"""

	today = frappe.utils.today()

	# get draft invoices whose period has ended or ends today
	invoices = frappe.db.get_all(
		"Invoice",
		filters={"status": "Draft", "type": "Subscription", "period_end": ("<=", today)},
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
			"payment_mode": ("in", ["Prepaid Credits", "Partner Credits"]),
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


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Invoice")


def calculate_gst(amount):
	return amount * 0.18
