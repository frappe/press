# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from datetime import datetime
from frappe.model.document import Document
from frappe.utils import rounded
from press.api.billing import get_stripe
from press.utils import log_error


class PaymentLedgerEntry(Document):
	def validate(self):
		if self.is_new():
			self.currency = frappe.db.get_value("Team", self.team, "transaction_currency")
			if self.purpose == "Site Consumption":
				# self.check_duplicate()
				self.calculate_consumption_amount()

	def check_duplicate(self):
		date = frappe.utils.nowdate()
		filters = {"site": self.site, "team": self.team, "plan": self.plan, "date": date}
		if frappe.db.exists("Payment Ledger Entry", filters):
			frappe.throw("This ledger entry already exists.", frappe.DuplicateEntryError)

	def calculate_consumption_amount(self):
		self.subscription = frappe.db.get_value(
			"Subscription", {"team": self.team, "status": "Active"}
		)
		price_field = "price_inr" if self.currency == "INR" else "price_usd"
		price, period = frappe.db.get_value("Plan", self.plan, [price_field, "period"])

		# Stripe will charge 0.01 amount per unit
		# and we can only send integers as unit
		# that is why price_per_day is rounded to 2 decimal places
		price_per_day = rounded(price / period, 2)
		# negative because this amount is used up
		self.amount = price_per_day * -1
		self.usage_units = price_per_day * 100
		self.timestamp = int(datetime.now().timestamp())
		self.date = frappe.utils.nowdate()

	def on_submit(self):
		if self.purpose == "Site Consumption":
			# create usage record on Stripe
			self.create_usage_record_on_stripe()
		elif self.purpose in ["Credits Allocation", "Reverse Credits Allocation"]:
			# create balance adjustment on Stripe
			self.create_balance_adjustment_on_stripe()

	def on_cancel(self):
		if self.purpose == "Credits Allocation":
			# reverse balance adjustment on Stripe
			doc = frappe.get_doc(
				{
					"doctype": "Payment Ledger Entry",
					"purpose": "Reverse Credits Allocation",
					"amount": self.amount * -1,
					"reversed_from": self.name,
					"team": self.team,
				}
			)
			doc.insert()
			doc.submit()

	def create_usage_record_on_stripe(self):
		stripe = get_stripe()
		if not self.subscription:
			frappe.throw("Subscription not created for {0}".format(self.team))

		subscription_item_id = frappe.db.get_value(
			"Subscription", self.subscription, "stripe_subscription_item_id"
		)
		usage_record = stripe.SubscriptionItem.create_usage_record(
			subscription_item_id,
			quantity=int(self.usage_units),
			timestamp=self.timestamp,
			action="increment",
			idempotency_key=self.name,
		)
		self.db_set("stripe_usage_record_id", usage_record["id"])

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

		doc = frappe.get_doc(
			{
				"doctype": "Payment Ledger Entry",
				"site": site.name,
				"purpose": "Site Consumption",
			}
		)
		doc.insert()
		try:
			doc.submit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Submit Payment Ledger Entry", doc=doc.name)


def submit_failed_ledger_entries():
	"""Will go through every Payment Ledger Entry for which usage record is not
	created on Stripe and will attempt to create it again."""

	entries = frappe.db.get_all(
		"Payment Ledger Entry",
		filters={"stripe_usage_record_id": "", "purpose": "Site Consumption", "docstatus": 0},
	)
	for entry in entries:
		try:
			frappe.get_doc("Payment Ledger Entry", entry.name).submit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Submit Failed Payment Ledger Entry", doc=doc.name)
