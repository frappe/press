# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from typing import List

import frappe
from frappe.model.document import Document
from frappe.utils import rounded


class Plan(Document):
	@property
	def period(self):
		return frappe.utils.get_last_day(None).day

	def get_price_per_day(self, currency):
		price = self.price_inr if currency == "INR" else self.price_usd
		price_per_day = rounded(price / self.period, 2)
		return price_per_day

	def get_price_for_interval(self, interval, currency):
		price_per_day = self.get_price_per_day(currency)

		if interval == "Daily":
			return price_per_day

		if interval == "Monthly":
			return rounded(price_per_day * 30)

	@classmethod
	def get_ones_without_offsite_backups(cls) -> List[str]:
		return frappe.get_all("Plan", filters={"offsite_backups": False}, pluck="name")


def get_plan_config(name):
	cpu_time = frappe.db.get_value("Plan", name, "cpu_time_per_day")
	if cpu_time > 0:
		return {"rate_limit": {"limit": cpu_time * 3600, "window": 86400}}
	return {}
