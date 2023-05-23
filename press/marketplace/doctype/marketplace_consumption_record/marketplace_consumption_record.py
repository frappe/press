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
			status = "Unpaid"
			self.status = status
			self.remark = "Not enough credits"
			self.update_invoice_status(status)

		self.disable_subscriptions(team)
		self.save()

	def allocate_credits(self, team=None):
		if not team:
			team = frappe.get_cached_doc("Team", self.team)

		team.allocate_credit_amount(
			self.amount * -1,
			source="Marketplace Consumption",
			remark="Consuming credits against prepaid marketplace subscriptions",
		)
		status = "Paid"
		self.status = status
		self.remark = "Charge Successful"
		self.update_invoice_status(status)

	def update_invoice_status(self, status):
		invoice_doc = frappe.get_cached_doc("Invoice", self.invoice)
		invoice_doc.status = status
		invoice_doc.save()

	def disable_subscriptions(self, team):
		if team.get_balance() > self.amount:
			return
		prepaid_apps = frappe.db.get_all(
			"Saas Settings", {"billing_type": "prepaid"}, pluck="name"
		)
		subs = frappe.db.get_all(
			"Marketplace App Subscription",
			{"app": ("in", prepaid_apps), "team": self.team},
			pluck="name",
		)

		for sub in subs:
			sub = frappe.get_cached_doc("Marketplace App Subscription", sub)
			sub.disable()


def consume_credits_for_prepaid_records():
	created = frappe.get_all(
		"Marketplace Consumption Record", {"status": "Unpaid"}, pluck="invoice", distinct=True
	)
	invs = frappe.get_all(
		"Invoice",
		{
			"name": ("not in", created),
			"status": ("in", ("Draft", "Unpaid")),
			"type": "Summary",
			"period_end": ("<=", frappe.utils.today()),
			"amount": (">", 0.0),
		},
		["name", "team", "total", "period_start", "period_end"],
	)

	current_time = frappe.utils.get_datetime().time()
	today = frappe.utils.getdate()

	for inv in invs:
		if inv.period_end == today and current_time.hour < 18:
			continue
		create_consumption_record(inv)


def create_consumption_record(inv):
	frappe.get_doc(
		{
			"doctype": "Marketplace Consumption Record",
			"team": inv["team"],
			"amount": inv["total"],
			"start_date": inv["period_start"],
			"end_date": inv["period_end"],
			"invoice": inv["name"],
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
