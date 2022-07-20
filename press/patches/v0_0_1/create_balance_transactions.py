# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe.utils import update_progress_bar
from press.api.billing import get_stripe


def execute():
	frappe.reload_doc("press", "doctype", "balance_transaction")

	partners = frappe.db.get_all("Team", filters={"erpnext_partner": 1}, pluck="name")
	for i, name in enumerate(partners):
		update_progress_bar("Creating Balance Transactions", i, len(partners))

		if frappe.db.exists(
			"Balance Transaction", {"team": name, "description": "Initial Balance"}
		):
			continue

		team = frappe.get_doc("Team", name)
		balance = team.get_stripe_balance()
		if balance != 0:
			stripe = get_stripe()
			# reset customer balance on Stripe
			stripe.Customer.create_balance_transaction(
				team.stripe_customer_id,
				# multiplied by 100 because Stripe wants amount in cents / paise
				amount=int(balance * 100),
				currency=team.currency.lower(),
				description="Reset customer balance",
				idempotency_key=team.name,
			)
			free_credits_left = get_free_credits_left(team)
			source = ""
			if free_credits_left == balance:
				source = "Free Credits"

			# set the balance as initial balance here
			team.allocate_credit_amount(balance, source=source, remark="Stripe Balance")


def get_free_credits_left(team):
	invoices = frappe.db.get_all("Invoice", {"team": team.name, "status": ("!=", "Draft")})

	settings = frappe.get_doc("Press Settings")
	total_free_credits = (
		settings.free_credits_inr if team.currency == "INR" else settings.free_credits_usd
	)

	if not invoices:
		return total_free_credits

	def sum(list):
		total = 0
		for d in list:
			total += d
		return total

	invoices_total = sum([invoice.total for invoice in invoices])
	if invoices_total < total_free_credits:
		return total_free_credits - invoices_total
	return 0
