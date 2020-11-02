# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import rounded

def _h(num: int) -> str:
	"""Assumes int data to describe size in MiB"""
	for unit in ['Mi', 'Gi','Ti','Pi','Ei','Zi']:
		if abs(num) < 1024:
			return f"{num:3.1f}{unit}B"
		num /= 1024
	return f"{num:.1f}YiB"

class Plan(Document):
	def validate(self):
		readable_mapped_fields = {
			"max_database_usage": "_max_database_usage",
			"max_storage_usage": "_max_storage_usage"
		}

		if not self.period:
			frappe.throw("Period must be greater than 0")

		for real, readable in readable_mapped_fields.items():
			num = self.get(real)
			if num:
				setattr(self, readable, _h(num))

	def get_price_per_day(self, currency):
		price = self.price_inr if currency == "INR" else self.price_usd
		price_per_day = rounded(price / self.period, 2)
		return price_per_day


def get_plan_config(name):
	cpu_time = frappe.db.get_value("Plan", name, "cpu_time_per_day")
	return {"rate_limit": {"limit": cpu_time * 3600, "window": 86400}}
