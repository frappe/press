# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from press.press.doctype.site_plan.plan import Plan


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
