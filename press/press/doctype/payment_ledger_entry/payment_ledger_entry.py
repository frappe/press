# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from datetime import datetime
from frappe.model.document import Document
from press.api.billing import get_stripe
from press.utils import log_error
from press.press.doctype.team.team_invoice import TeamInvoice


class PaymentLedgerEntry(Document):
	def validate(self):
		if self.is_new():
			currency, free_account = frappe.db.get_value(
				"Team", self.team, ["currency", "free_account"]
			)
			free_site = frappe.db.get_value("Site", self.site, "free")
			self.currency = currency
			self.free_usage = free_account or free_site or False

			if self.purpose == "Site Consumption":
				if not frappe.conf.developer_mode:
					self.check_duplicate()
				self.calculate_consumption_amount()

	def check_duplicate(self):
		date = frappe.utils.nowdate()
		filters = {
			"site": self.site,
			"team": self.team,
			"plan": self.plan,
			"date": date,
			"docstatus": ("<", 2),
		}
		existing_ledger = frappe.db.exists("Payment Ledger Entry", filters)
		if existing_ledger:
			link = frappe.utils.get_link_to_form("Payment Ledger Entry", existing_ledger)
			frappe.throw(
				"Duplicate Entry {0} already exists.".format(link), frappe.DuplicateEntryError
			)

	def calculate_consumption_amount(self):
		plan = frappe.get_doc("Plan", self.plan)
		# Stripe will charge 0.01 amount per unit
		# and we can only send integers as unit
		# that is why price_per_day is rounded to 2 decimal places
		price_per_day = plan.get_price_per_day(self.currency)
		# negative because this amount is used up
		self.amount = price_per_day * -1
		self.usage_units = price_per_day * 100
		self.timestamp = int(datetime.now().timestamp())
		self.date = frappe.utils.nowdate()

	def on_submit(self):
		if self.purpose == "Site Consumption":
			self.update_usage_in_invoice()
		elif self.purpose in ["Credits Allocation", "Reverse Credits Allocation"]:
			self.create_balance_adjustment_on_stripe()

	def on_cancel(self):
		if self.purpose == "Site Consumption":
			self.remove_usage_from_invoice()

	def revert(self, reason=None):
		if self.purpose == "Credits Allocation":
			# reverse balance adjustment on Stripe
			doc = frappe.get_doc(
				{
					"doctype": "Payment Ledger Entry",
					"purpose": "Reverse Credits Allocation",
					"amount": self.amount * -1,
					"reverted_from": self.name,
					"team": self.team,
				}
			)
			doc.insert()
			doc.submit()
			if reason:
				doc.add_comment(text=reason)
			self.reverted = 1
			self.save()

	def update_usage_in_invoice(self):
		if self.purpose != "Site Consumption":
			return
		if self.invoice:
			return
		if self.free_usage:
			return
		date = frappe.utils.getdate(self.date)
		ti = TeamInvoice(self.team, date.month, date.year)
		# if invoice is not created for this month create it
		if not ti.get_draft_invoice() and date.month > 6 and date.year > 2020:
			ti.create()
		ti.update_site_usage(self)

	def remove_usage_from_invoice(self):
		if self.purpose != "Site Consumption":
			return
		if not self.invoice:
			return
		if self.free_usage:
			return
		date = frappe.utils.getdate(self.date)
		ti = TeamInvoice(self.team, date.month, date.year)
		invoice = frappe.get_doc("Invoice", self.invoice)
		ti.remove_ledger_entry_from_invoice(self, invoice)

	def create_balance_adjustment_on_stripe(self):
		stripe = get_stripe()
		# add amount to customer balance
		# negative value is credit to the customer's balance on Stripe
		amount = (self.amount) * -1

		customer_id = frappe.db.get_value("Team", self.team, "stripe_customer_id")
		transaction = stripe.Customer.create_balance_transaction(
			customer_id,
			# multiplied by 100 because Stripe wants amount in cents / paise
			amount=int(amount * 100),
			currency=self.currency.lower(),
			description=self.purpose,
			idempotency_key=self.name,
		)
		self.db_set("stripe_customer_balance_transaction_id", transaction["id"])

	def increment_failed_attempt(self):
		self.failed_submission_attempts = self.failed_submission_attempts or 0
		self.failed_submission_attempts += 1
		self.save()


def create_ledger_entries():
	"""Creates a Payment Ledger Entry for each active site.
	This runs hourly but will only create one record per day for each site"""
	today = frappe.utils.nowdate()
	active_sites = frappe.db.get_all(
		"Site",
		filters=[
			["status", "=", "Active"],
			["team", "is", "set"],
			["team", "!=", "Administrator"],
			["plan", "is", "set"],
		],
		fields=["name", "team", "plan"],
	)
	for site in active_sites:
		filters = {"site": site.name, "team": site.team, "plan": site.plan, "date": today}
		if frappe.db.exists("Payment Ledger Entry", filters):
			continue

		frappe.get_doc("Site", site.name).create_usage_ledger_entry()


def submit_failed_ledger_entries():
	"""Will go through every Payment Ledger Entry for which usage is not updated in Invoice
	and will attempt to update it again."""

	entries = frappe.db.get_all(
		"Payment Ledger Entry",
		filters={
			"invoice": "",
			"purpose": "Site Consumption",
			# get entries that have failed less than 3 times
			"failed_submission_attempts": ("<", 3),
			"free_usage": False,
		},
	)
	for entry in entries:
		try:
			doc = frappe.get_doc("Payment Ledger Entry", entry.name)
			if doc.docstatus == 0:
				doc.submit()
				doc.reload()
			if not doc.invoice:
				doc.update_usage_in_invoice()
		except Exception:
			frappe.db.rollback()
			log_error(title="Update PLE Usage in invoice failed", doc=doc.name)
			doc.reload()
			doc.increment_failed_attempt()
