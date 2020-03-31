# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Plan(Document):
	def get_plan_id(self, currency='USD'):
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
