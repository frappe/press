# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from datetime import datetime
from frappe.model.document import Document
from frappe.utils import rounded
from press.api.billing import get_stripe


class SiteUsageLedgerEntry(Document):
	def validate(self):
		self.check_duplicate()

	def check_duplicate(self):
		date = frappe.utils.nowdate()
		filters = {"site": self.site, "team": self.team, "plan": self.plan, "date": date}
		if frappe.db.exists("Site Usage Ledger Entry", filters):
			frappe.throw("This ledger entry already exists.", frappe.DuplicateEntryError)

	def before_insert(self):
		self.currency = frappe.db.get_value("Team", self.team, "transaction_currency")
		price_field = "price_inr" if self.currency == "INR" else "price_usd"
		price = frappe.db.get_value("Plan", self.plan, price_field)
		# 30 days
		price_per_day = price / 30
		# Stripe will charge 0.01 amount / unit
		# and we can only send integers as unit
		# that is why the value is rounded to 2 decimal places
		charge_per_unit = 0.01
		rounded_value = rounded(price_per_day, 2)
		self.usage_units = rounded_value * 100
		self.usage_value = self.usage_units * charge_per_unit
		self.timestamp = int(datetime.now().timestamp())
		self.date = frappe.utils.nowdate()

	def after_insert(self):
		# try creating usage record on Stripe
		# it can fail, but we can try to push it later
		try:
			self.create_usage_record_on_stripe()
		except Exception:
			frappe.log_error()

	def create_usage_record_on_stripe(self):
		stripe = get_stripe()
		subscription_item_id = frappe.db.get_value(
			"Subscription", self.subscription, "stripe_subscription_item_id"
		)
		usage_record = stripe.SubscriptionItem.create_usage_record(
			subscription_item_id,
			quantity=self.usage_units,
			timestamp=self.timestamp,
			action="increment",
			idempotency_key=self.name,
		)
		self.db_set("stripe_usage_record_id", usage_record["id"])


def create_ledger_entries():
	"""Creates a Site Usage Ledger Entry for each active site.
	This runs hourly but will only create one record per day for each site"""

	active_sites = frappe.db.get_all(
		"Site", filters={"status": "Active"}, fields=["name", "team", "plan"]
	)
	for site in active_sites:
		date = frappe.utils.nowdate()
		filters = {"site": site.name, "team": site.team, "plan": site.plan, "date": date}
		if frappe.db.exists("Site Usage Ledger Entry", filters):
			continue

		subscription = frappe.db.get_value(
			"Subscription", filters={"team": site.team, "status": "Active"}
		)
		frappe.get_doc(
			{
				"doctype": "Site Usage Ledger Entry",
				"site": site.name,
				"team": site.team,
				"plan": site.plan,
				"subscription": subscription,
			}
		).insert()


def create_usage_record_for_failed_requests():
	"""Will go through every Site Usage Ledger Entry for which usage record is not
	created on Stripe and will attempt to create it again."""

	entries = frappe.db.get_all(
		"Site Usage Ledger Entry", filters={"stripe_usage_record_id": ""}
	)
	for entry in entries:
		frappe.get_doc("Site Usage Ledger Entry", entry.name).create_usage_record_on_stripe()
