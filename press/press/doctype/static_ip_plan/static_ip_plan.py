# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class StaticIPPlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		price_inr: DF.Currency
		price_usd: DF.Currency
		provider: DF.Literal["AWS EC2"]
		title: DF.Data | None
	# end: auto-generated types

	def get_price_for_interval(self, interval, currency):
		price = self.price_inr if currency == "INR" else self.price_usd

		if interval == "Daily":
			return frappe.utils.flt(price, 2)

		frappe.throw("Invalid interval. Interval must be either 'Hourly' or 'Daily'.")
		return 0.0
