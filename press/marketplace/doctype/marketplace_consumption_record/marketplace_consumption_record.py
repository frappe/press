# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceConsumptionRecord(Document):
	def after_insert(self):
		team = frappe.get_cached_doc("Team", self.team)
		if team.get_balance() >= self.amount and self.status in ["Draft", "Unpaid"]:
			self.allocate_credits(team)
		else:
			self.status = "Unpaid"
			self.remark = "Not enough credits"

		self.save()

	def allocate_credits(self, team=None):
		if not team:
			team = frappe.get_cached_doc("Team", self.team)

		team.allocate_credit_amount(
			self.amount * -1,
			source="Marketplace Consumption",
			remark="Consuming credits against prepaid marketplace subscriptions",
		)
		self.status = "Paid"
		self.remark = "Charge Successful"


def consume_credits_for_prepaid_records():
	invs = frappe.get_all("Invoice", {"status": "Draft", "type": "Summary"}, pluck="name")

	for inv in invs:
		invoice_doc = frappe.get_cached_doc("Invoice", inv)
		frappe.get_doc(
			{
				"doctype": "Marketplace Consumption Record",
				"team": invoice_doc.team,
				"amount": invoice_doc.total,
				"start_date": invoice_doc.period_start,
				"end_date": invoice_doc.period_end,
			}
		).insert(ignore_permissions=True)

		invoice_doc.status = "Uncollectible"
		invoice_doc.save()