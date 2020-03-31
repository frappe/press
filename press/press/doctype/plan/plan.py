# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.api.billing import get_stripe


class Plan(Document):
	def before_insert(self):
		self.title = self.title or self.name
		stripe = get_stripe()
		product = stripe.Product.create(name=self.name, type="service")
		self.stripe_product_id = product.id

		usd_plan = stripe.Plan.create(
			usage_type="metered",
			aggregate_usage="sum",
			currency="usd",
			interval="month",
			product=product.id,
			nickname="USD Monthly",
			amount_decimal="1",
		)
		inr_plan = stripe.Plan.create(
			usage_type="metered",
			aggregate_usage="sum",
			currency="inr",
			interval="month",
			product=product.id,
			nickname="INR Monthly",
			amount_decimal="1",
		)

		self.stripe_inr_plan_id = inr_plan.id
		self.stripe_usd_plan_id = usd_plan.id

	def get_plan_id(self, currency="USD"):
		plan_id = None
		for plan in self.plan_details:
			if plan.currency == currency:
				plan_id = plan.plan_id
				break

		return plan_id

	def get_units_to_charge(self, team):
		currency = frappe.db.get_value("Team", team, "transaction_currency")
		pricing_factor = 1

		for plan in self.plan_details:
			if plan.currency == currency:
				pricing_factor = plan.pricing_factor
				break

		return pricing_factor
