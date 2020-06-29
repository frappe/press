# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class Plan(Document):
	def validate(self):
		if not self.period:
			frappe.throw("Period must be greater than 0")


def get_plan_config(name):
	cpu_time = frappe.db.get_value("Plan", name, "cpu_time_per_day")
	return {"rate_limit": {"limit": cpu_time * 3600, "window": 86400}}
