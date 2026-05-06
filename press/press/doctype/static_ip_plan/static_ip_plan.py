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
		if interval != "Hourly":
			frappe.throw("Only hourly interval is supported for Static IP Plan")

		if currency == "INR":
			return frappe.utils.flt(self.price_inr, 2)
		if currency == "USD":
			return frappe.utils.flt(self.price_usd, 2)

		frappe.throw(f"Currency {currency} is not supported for Static IP Plan")
		return 0.0
