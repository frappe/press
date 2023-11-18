# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.overrides import get_permission_query_conditions_for_doctype


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
			if self.unallocated_amount < 0:
				# in case of credit transfer
				self.allocate_to_previous_transaction()
				self.unallocated_amount = 0

	def before_update_after_submit(self):
		total_allocated = sum([d.amount for d in self.allocated_to])
		self.unallocated_amount = self.amount - total_allocated

	def on_submit(self):
		frappe.publish_realtime("balance_updated", user=self.team)

	def allocate_to_previous_transaction(self):
		previous_transaction = (
			frappe.get_all(
				"Balance Transaction",
				filters={
					"docstatus": 1,
					"team": self.team,
					"unallocated_amount": (">", 0)
				},
				order_by="creation desc",
				pluck="name",
				limit=1,
			)
			or []
		)
		if not previous_transaction:
			frappe.throw(
				"Cannot reduce unallocated amount from previous transaction as no previous transaction found"
			)
		previous_transaction = frappe.get_doc(
			"Balance Transaction", previous_transaction[0]
		)
		previous_transaction.append("allocated_to", {
			"amount": -1 * self.amount,
			"currency": self.currency,
			"balance_transaction": self.name,
		})
		previous_transaction.save(ignore_permissions=True)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Balance Transaction"
)
