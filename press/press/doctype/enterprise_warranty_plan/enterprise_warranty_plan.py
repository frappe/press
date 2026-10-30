# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class EnterpriseWarrantyPlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		coverage: DF.SmallText | None
		description: DF.Data | None
		enabled: DF.Check
		max_price_lock_years: DF.Int
		price_inr: DF.Currency
		price_usd: DF.Currency
		title: DF.Data
	# end: auto-generated types

	def validate(self):
		if self.max_price_lock_years < 1:
			frappe.throw("Max price lock period must be at least 1 year")

	def get_price(self, currency: str) -> float:
		return self.price_inr if currency == "INR" else self.price_usd

	@property
	def price_lock_years(self) -> list[int]:
		return list(range(1, self.max_price_lock_years + 1))

	def as_dashboard(self, currency: str) -> dict:
		price = self.get_price(currency)
		return {
			"name": self.name,
			"title": self.title,
			"description": self.description,
			"currency": currency,
			"yearly_price": price,
			"amount_due": amount_due(price, currency),
			"amount_due_with_credits": amount_due(price, currency, with_gst=False),
			"price_lock_years": self.price_lock_years,
			"coverage": (self.coverage or "").strip().splitlines(),
		}


def enabled_plans(currency: str) -> list[dict]:
	names = frappe.get_all("Enterprise Warranty Plan", {"enabled": 1}, pluck="name", order_by="price_usd asc")
	return [frappe.get_cached_doc("Enterprise Warranty Plan", name).as_dashboard(currency) for name in names]


def gst_rate() -> float:
	return flt(frappe.db.get_single_value("Press Settings", "gst_percentage"))


# Credits were taxed when they were bought, so paying with them adds no GST.
def amount_due(price: float, currency: str, with_gst: bool = True) -> dict:
	gst = flt(price * gst_rate(), 2) if with_gst and currency == "INR" else 0
	return {"amount": price, "gst": gst, "total": price + gst}
