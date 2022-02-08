# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe
from press.api.billing import get_stripe
from datetime import datetime

migrated_cache_key = "migrated_teams"


def execute():
	frappe.reload_doc("press", "doctype", "balance_transaction")

	skip_teams = list(frappe.cache().smembers(migrated_cache_key))
	teams = frappe.db.get_all(
		"Team",
		filters={"name": ("not in", skip_teams), "stripe_customer_id": ("is", "set")},
		pluck="name",
	)
	for name in teams:
		try:
			create_balance_transactions_for_team(name)
			frappe.cache().sadd(migrated_cache_key, name)
		except Exception:
			print(f"❗️ Failed for {name}")
			print(frappe.get_traceback())


def create_balance_transactions_for_team(name):
	team = frappe.get_doc("Team", name)
	stripe = get_stripe()
	# skip if already done
	if frappe.db.exists(
		"Balance Transaction", {"source": "Free Credits", "team": team.name}
	):
		print(f"Skipping for {team.name}")
		return

	print(f"Creating Balance Transactions for {team.name}")

	response = stripe.Customer.list_balance_transactions(
		team.stripe_customer_id, limit=100
	)
	transactions = response.data
	transactions.reverse()

	if team.free_credits_allocated:
		free_credits_left = 1800 if team.currency == "INR" else 25
	else:
		free_credits_left = 0

	balance_transactions = []
	free_credit_balance_created = False
	for transaction in transactions:
		amount = transaction.amount * -1 / 100
		type = (
			"Applied To Invoice" if transaction.type == "applied_to_invoice" else "Adjustment"
		)
		source = ""
		invoice_name = ""
		if type == "Adjustment":
			if amount > 0:
				free_credits = 1800 if transaction.currency == "inr" else 25
				source = (
					"Free Credits"
					if team.free_credits_allocated
					and amount == free_credits
					and not free_credit_balance_created
					else "Transferred Credits"
				)

		if type == "Applied To Invoice":
			invoice = frappe.get_doc("Invoice", {"stripe_invoice_id": transaction.invoice})
			invoice_name = invoice.name
			free_credits_applied = apply_to_invoice(
				invoice, amount, free_credits_left, balance_transactions
			)
			free_credits_left = frappe.utils.rounded(free_credits_left - free_credits_applied, 2)

		bt = create_balance_transaction(
			team,
			amount=amount,
			source=source,
			type=type,
			invoice=invoice_name,
			creation=datetime.fromtimestamp(transaction.created),
		)
		balance_transactions.append(bt)
		if bt.source == "Free Credits":
			free_credit_balance_created = True

	stripe_balance = team.get_stripe_balance()
	team_balance = team.get_balance()
	if stripe_balance == team_balance:
		reset_customer_balance_on_stripe(team)
		frappe.db.commit()
		print(f"✅ Successful for {team.name}")
	else:
		frappe.db.rollback()
		print(
			f"❌ Balance mismatch for {team.name}. Team Balance: {team_balance}, Stripe"
			f" Balance: {stripe_balance}"
		)


def apply_to_invoice(invoice, amount, free_credits_left, balance_transactions):
	unallocated_bts = get_last_unallocated_balance_transactions(balance_transactions)
	amount_to_apply = amount * -1
	applied = 0
	not_applied = amount_to_apply - applied
	free_credits_applied = 0
	_free_credits_left = free_credits_left
	for bt in unallocated_bts:
		if applied == amount_to_apply:
			break

		if _free_credits_left:
			to_apply = min(not_applied, _free_credits_left)
			if to_apply > bt.unallocated_amount:
				to_apply = bt.unallocated_amount
			free_credits_applied += to_apply
			_free_credits_left -= to_apply
		else:
			to_apply = not_applied
			if to_apply > bt.unallocated_amount:
				to_apply = bt.unallocated_amount

		invoice.append(
			"credit_allocations",
			{
				"transaction": bt.name,
				"source": bt.source,
				"amount": to_apply,
				"currency": invoice.currency,
			},
		)
		row = bt.append(
			"allocated_to",
			{"invoice": invoice.name, "amount": to_apply, "currency": invoice.currency},
		)
		bt.save()
		bt.reload()
		applied += to_apply
		not_applied = amount_to_apply - applied

	for row in invoice.credit_allocations:
		row.db_insert()

	return free_credits_applied


def reset_customer_balance_on_stripe(team):
	stripe = get_stripe()
	balance = team.get_stripe_balance()
	if balance != 0:
		stripe.Customer.create_balance_transaction(
			team.stripe_customer_id,
			# multiplied by 100 because Stripe wants amount in cents / paise
			# to reset the balance we should provide negative value of the original value
			# but we store the credit balance as a positive and stripe stores it as negative
			# so a positive value will negate the value to 0 on stripe
			amount=int(balance * 100),
			currency=team.currency.lower(),
			description="Reset customer balance",
			idempotency_key=team.name,
		)


def get_last_unallocated_balance_transactions(balance_transactions):
	out = []
	adjustments = [d for d in balance_transactions if d.type == "Adjustment"]
	for bt in adjustments:
		if bt.unallocated_amount > 0:
			out.append(bt)
	return out


def create_balance_transaction(team, **kwargs):
	doc = frappe.get_doc(doctype="Balance Transaction", team=team.name)
	doc.update(kwargs)
	doc.insert(ignore_permissions=True)
	doc.submit()
	doc.reload()
	return doc
