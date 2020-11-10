# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class BalanceTransaction(Document):
	def validate(self):
		if self.amount == 0:
			frappe.throw("Amount cannot be 0")

	def before_submit(self):
		res = frappe.db.get_all(
			"Balance Transaction",
			filters={"team": self.team, "docstatus": 1},
			fields=["sum(amount) as ending_balance"],
			group_by="team",
			pluck="ending_balance",
		)
		if res:
			self.ending_balance = (res[0] or 0) + self.amount
		else:
			self.ending_balance = self.amount
