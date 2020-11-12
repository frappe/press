# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals

import frappe
from press.api.billing import get_stripe
from datetime import datetime


@frappe.whitelist()
def execute():
	frappe.reload_doc("press", "doctype", "balance_transaction")

	teams = frappe.db.get_all("Team", pluck="name")
	stripe = get_stripe()

	for name in teams:
		team = frappe.get_doc("Team", name)
		print(f"Creating Balance Transactions for {team.name}")

		# skip if already done
		if frappe.db.exists(
			"Balance Transaction", {"source": "Free Credits", "team": team.name}
		):
			print(f"Skipping for {team.name}")
			continue

		response = stripe.Customer.list_balance_transactions(
			team.stripe_customer_id, limit=100,
		)
		transactions = response.data
		transactions.reverse()

		free_credits_left = 1800 if team.currency == "INR" else 25
		balance_transactions = []
		free_credit_balance_created = False
		for transaction in transactions:
			free_credits = 1800 if transaction.currency == "inr" else 25
			amount = transaction.amount * -1 / 100
			type = (
				"Applied To Invoice" if transaction.type == "applied_to_invoice" else "Adjustment"
			)
			source = ""
			invoice_name = ""
			if type == "Adjustment":
				if amount > 0:
					source = (
						"Free Credits"
						if amount == free_credits and not free_credit_balance_created
						else "Transferred Credits"
					)

			if type == "Applied To Invoice":
				invoice = frappe.get_doc("Invoice", {"stripe_invoice_id": transaction.invoice})
				invoice_name = invoice.name
				free_credits_applied = apply_to_invoice(
					invoice, amount, free_credits_left, balance_transactions
				)
				free_credits_left -= free_credits_applied

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

		reset_customer_balance_on_stripe(team)
		frappe.db.commit()


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
		bt.append(
			"allocated_to",
			{"invoice": invoice.name, "amount": to_apply, "currency": invoice.currency},
		)
		bt.save()
		applied += to_apply
		not_applied = amount_to_apply - applied

	for row in invoice.credit_allocations:
		row.db_update()

	return free_credits_applied


def reset_customer_balance_on_stripe(team):
	stripe = get_stripe()
	balance = team.get_stripe_balance()
	if balance != 0:
		stripe.Customer.create_balance_transaction(
			team.stripe_customer_id,
			# multiplied by 100 because Stripe wants amount in cents / paise
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
	# doc.db_set("creation", kwargs.get("creation"), update_modified=False)
	doc.submit()
	return doc
