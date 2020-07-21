# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.api.billing import get_stripe
from datetime import datetime


class Subscription(Document):
	def before_insert(self):
		stripe = get_stripe()
		# get customer, currency, payment method from team
		customer_id, currency = frappe.db.get_value(
			"Team", self.team, ["stripe_customer_id", "currency"],
		)
		# get plan id from plan
		plan_id_field = "stripe_inr_plan_id" if currency == "INR" else "stripe_usd_plan_id"
		plan_id = frappe.db.get_single_value("Press Settings", plan_id_field)

		subscription = stripe.Subscription.create(
			customer=customer_id, items=[{"plan": plan_id}],
		)
		self.stripe_subscription_id = subscription.id
		self.stripe_subscription_item_id = subscription["items"]["data"][0]["id"]
