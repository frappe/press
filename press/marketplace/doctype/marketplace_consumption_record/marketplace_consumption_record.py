# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MarketplaceConsumptionRecord(Document):
	def after_insert(self):
		team = frappe.get_cached_doc("Team", self.team)
		if team.get_balance() >= self.amount and self.status in ["Draft", "Unpaid"]:
			self.charge(team)
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
	start_date, end_date = date_range()
	usage_records = frappe.get_all(
		"Usage Record",
		{"date": ("between", (start_date, end_date)), "prepaid": 1},
		["sum(amount) as amount", "team"],
		group_by="team",
	)

	for rec in usage_records:
		frappe.get_doc(
			{
				"doctype": "Marketplace Consumption Record",
				"team": rec["team"],
				"amount": rec["amount"],
				"start_date": start_date,
				"end_date": end_date,
			}
		).insert(ignore_permissions=True)


def date_range():
	import datetime

	today = datetime.datetime.today().date()
	next_month = today.replace(day=28) + datetime.timedelta(days=4)
	first_day = str(today.replace(day=1))
	last_day = str(next_month - datetime.timedelta(days=next_month.day))

	return (first_day, last_day)
