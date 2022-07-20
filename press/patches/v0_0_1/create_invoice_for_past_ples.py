# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from datetime import datetime
from press.api.billing import get_stripe
from press.press.doctype.team.team_invoice import TeamInvoice

# - Cancel subscription
# - Create old invoices
# - Create running draft invoice

migrated_cache_key = "migrated_teams"
traceback_cache_key = "team_traceback"
total_match_failure_key = "total_match_failure"
failed_subscriptions = "failed_subscriptions"


def execute():
	skip_teams = list(frappe.cache().smembers(migrated_cache_key))
	for d in frappe.db.get_all("Team", filters={"name": ("not in", skip_teams)}):
		migrate_team(d.name)


def migrate_team(team):
	try:
		cancel_subscription(team)
		last_invoice_period_end = create_past_invoices(team)
		create_draft_invoice(team, last_invoice_period_end)
		frappe.db.commit()
		frappe.cache().sadd(migrated_cache_key, team)
		log(team, message="migration_success")
	except Exception:
		frappe.cache().hset(traceback_cache_key, team, frappe.get_traceback())
		frappe.db.rollback()
		log(team, message="migration_failed ❌")
	print()


def cancel_subscription(team):
	stripe = get_stripe()
	subscription_id = frappe.db.get_value(
		"Subscription", {"team": team}, "stripe_subscription_id"
	)
	if subscription_id:
		try:
			stripe.Subscription.delete(subscription_id)
		except Exception:
			log(team, message="cancel_subscription_failed ❌")
			frappe.cache().sadd(failed_subscriptions, subscription_id)


def create_past_invoices(team):
	team = frappe.get_doc("Team", team)
	stripe = get_stripe()
	res = stripe.Invoice.list(customer=team.stripe_customer_id)
	# remove the invoice with 0 amount
	invoices = [d for d in res["data"] if d["total"] != 0]
	# sort into ascending order of creation
	invoices.reverse()

	last_invoice_period_end = None

	for index, invoice in enumerate(invoices):
		i = frappe.new_doc("Invoice")
		i.team = team.name
		i.customer_name = frappe.utils.get_fullname(team.user)
		i.customer_email = team.user
		i.currency = team.currency
		i.period_start = datetime.fromtimestamp(invoice["period_start"])
		if index != 0:
			i.period_start = frappe.utils.add_days(i.period_start, 1)
		i.period_end = datetime.fromtimestamp(invoice["period_end"])
		i.stripe_invoice_id = invoice["id"]
		i.starting_balance = invoice["starting_balance"] / 100
		i.ending_balance = (invoice["ending_balance"] or 0) / 100
		i.amount_due = invoice["amount_due"] / 100
		i.amount_paid = invoice["amount_paid"] / 100
		i.stripe_invoice_url = invoice["hosted_invoice_url"]

		if invoice["status"] == "paid":
			i.payment_date = datetime.fromtimestamp(invoice["status_transitions"]["paid_at"])
			i.status = "Paid"
		else:
			i.status = "Overdue"
		i.payment_attempt_count = invoice.get("attempt_count")

		last_invoice_period_end = i.period_end

		i.save()
		i.reload()

		entries = frappe.db.get_all(
			"Payment Ledger Entry",
			filters={
				"creation": ("between", [i.period_start, i.period_end]),
				"purpose": "Site Consumption",
				"team": team.name,
				"docstatus": 1,
				"free_usage": False,
			},
		)
		for e in entries:
			ledger_entry = frappe.get_doc("Payment Ledger Entry", e.name)
			TeamInvoice(
				team, i.period_start.month, i.period_start.year
			).update_ledger_entry_in_invoice(ledger_entry, i)

		i.reload()
		if i.total == (invoice["total"] / 100):
			log(
				team.name,
				invoice=i.name,
				stripe_invoice=invoice["id"],
				message="total_match_success",
			)
			i.db_set("docstatus", 1)
		else:
			log(
				team.name,
				invoice=i.name,
				stripe_invoice=invoice["id"],
				message="total_match_failure ❌",
			)
			frappe.cache().sadd(total_match_failure_key, i.name)
	return last_invoice_period_end


def create_draft_invoice(team, last_invoice_period_end=None):
	if not last_invoice_period_end:
		# no invoices has been created yet
		# create an invoice when they joined
		period_start = frappe.db.get_value("Team", team, "creation")
	else:
		period_start = frappe.utils.add_days(last_invoice_period_end, 1)

	invoice = TeamInvoice(team, period_start.month, period_start.year).create(period_start)

	entries = frappe.db.get_all(
		"Payment Ledger Entry",
		filters={
			"creation": ("between", [invoice.period_start, invoice.period_end]),
			"purpose": "Site Consumption",
			"team": team,
			"docstatus": 1,
			"free_usage": False,
		},
	)
	for e in entries:
		ledger_entry = frappe.get_doc("Payment Ledger Entry", e.name)
		ledger_entry.update_usage_in_invoice()

	log(team, invoice=invoice.name, message="created_draft_invoice")


def log(team, invoice=None, stripe_invoice=None, message=None):
	text = "  \t  ".join([team, invoice or "", stripe_invoice or "", message or ""])
	frappe.cache().lpush("migrate_log", text)
	print(text)
