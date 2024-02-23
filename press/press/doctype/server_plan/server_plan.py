# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.press.doctype.site_plan.plan import Plan
from frappe.utils import rounded


class ServerPlan(Plan):
	dashboard_fields = [
		"title",
		"price_inr",
		"price_usd",
		"vcpu",
		"memory",
		"disk",
	]

	def get_doc(self, doc):
		doc["price_per_day_inr"] = self.get_price_per_day("INR")
		doc["price_per_day_usd"] = self.get_price_per_day("USD")
		return doc

	@property
	def period(self):
		return frappe.utils.get_last_day(None).day

	def get_price_per_day(self, currency):
		price = self.price_inr if currency == "INR" else self.price_usd
		price_per_day = rounded(price / self.period, 2)
		return price_per_day
