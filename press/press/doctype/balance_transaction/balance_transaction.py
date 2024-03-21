# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.overrides import get_permission_query_conditions_for_doctype


class BalanceTransaction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.balance_transaction_allocation.balance_transaction_allocation import (
			BalanceTransactionAllocation,
		)

		allocated_to: DF.Table[BalanceTransactionAllocation]
		amended_from: DF.Link | None
		amount: DF.Currency
		currency: DF.Link | None
		description: DF.SmallText | None
		ending_balance: DF.Currency
		invoice: DF.Data | None
		source: DF.Literal[
			"",
			"Prepaid Credits",
			"Free Credits",
			"Transferred Credits",
			"Discount",
			"Referral Bonus",
			"Marketplace Consumption",
		]
		team: DF.Link
		type: DF.Literal["Adjustment", "Applied To Invoice"]
		unallocated_amount: DF.Currency
	# end: auto-generated types

	dashboard_fields = ["type", "amount", "ending_balance", "invoice", "source"]

	def validate(self):
		if self.amount == 0:
			frappe.throw("Amount cannot be 0")

	def before_submit(self):
		last_balance = frappe.db.get_all(
			"Balance Transaction",
			filters={"team": self.team, "docstatus": 1},
			fields=["sum(amount) as ending_balance"],
			group_by="team",
			pluck="ending_balance",
		)
		last_balance = last_balance[0] if last_balance else 0
		if last_balance:
			self.ending_balance = (last_balance or 0) + self.amount
		else:
			self.ending_balance = self.amount

		if self.type == "Adjustment":
			self.unallocated_amount = self.amount
			if self.unallocated_amount < 0:
				# in case of credit transfer
				self.consume_unallocated_amount()
				self.unallocated_amount = 0
			elif last_balance < 0 and abs(last_balance) <= self.amount:
				# previously the balance was negative
				# settle the negative balance
				self.unallocated_amount = self.amount - abs(last_balance)
				self.add_comment(text=f"Settling negative balance of {abs(last_balance)}")
			elif last_balance < 0 and abs(last_balance) > self.amount:
				# doesn't make sense to throw because payment happens before creating BT
				pass

	def before_update_after_submit(self):
		total_allocated = sum([d.amount for d in self.allocated_to])
		self.unallocated_amount = self.amount - total_allocated

	def on_submit(self):
		frappe.publish_realtime("balance_updated", user=self.team)

	def consume_unallocated_amount(self):
		self.validate_total_unallocated_amount()

		allocation_map = {}
		remaining_amount = abs(self.amount)
		transactions = frappe.get_all(
			"Balance Transaction",
			filters={"docstatus": 1, "team": self.team, "unallocated_amount": (">", 0)},
			fields=["name", "unallocated_amount"],
			order_by="creation asc",
		)
		for transaction in transactions:
			if remaining_amount <= 0:
				break
			allocated_amount = min(remaining_amount, transaction.unallocated_amount)
			remaining_amount -= allocated_amount
			allocation_map[transaction.name] = allocated_amount

		for transaction, amount in allocation_map.items():
			doc = frappe.get_doc("Balance Transaction", transaction)
			doc.append(
				"allocated_to",
				{
					"amount": abs(amount),
					"currency": self.currency,
					"balance_transaction": self.name,
				},
			)
			doc.save(ignore_permissions=True)

	def validate_total_unallocated_amount(self):
		total_unallocated_amount = (
			frappe.get_all(
				"Balance Transaction",
				filters={"docstatus": 1, "team": self.team, "unallocated_amount": (">", 0)},
				fields=["sum(unallocated_amount) as total_unallocated_amount"],
				pluck="total_unallocated_amount",
			)
			or []
		)
		if not total_unallocated_amount:
			frappe.throw("Cannot create transaction as no unallocated amount found")
		if total_unallocated_amount[0] < abs(self.amount):
			frappe.throw(
				f"Cannot create transaction as unallocated amount {total_unallocated_amount[0]} is less than {self.amount}"
			)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Balance Transaction"
)
