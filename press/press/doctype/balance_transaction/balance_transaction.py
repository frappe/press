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

		if self.type == "Adjustment":
			self.unallocated_amount = self.amount

	def before_update_after_submit(self):
		total_allocated = sum([d.amount for d in self.allocated_to])
		self.unallocated_amount = self.amount - total_allocated

	def on_submit(self):
		frappe.publish_realtime("balance_updated", user=self.team)


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabBalance Transaction`.`team` = {frappe.db.escape(team)})"


def has_permission(doc, ptype, user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return True

	team = get_current_team()
	if doc.team == team:
		return True

	return False
