# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Spread each yearly contract payment over 12 months of partner contribution, without touching invoices."""

from __future__ import annotations

import json

import frappe
from frappe.utils import (
	add_months,
	flt,
	get_date_str,
	get_first_day,
	get_last_day,
	getdate,
	month_diff,
	today,
)

from press.press.doctype.enterprise_contract.enterprise_contract import OPEN_STATUSES
from press.utils.billing import get_frappe_io_connection

MONTHS_IN_YEAR = 12
TRANSACTION_TYPE = "Enterprise Contract"
TRANSACTION_ENDPOINT = "create_partner_transaction_for_fc_invoice"


def contract_shares(month, partner_emails: list[str]) -> list[frappe._dict]:
	if not partner_emails:
		return []
	month = get_first_day(month)
	payment = frappe.qb.DocType("Enterprise Contract Payment")
	contract = frappe.qb.DocType("Enterprise Contract")
	team = frappe.qb.DocType("Team")
	rows = (
		frappe.qb.from_(payment)
		.join(contract)
		.on(payment.parent == contract.name)
		.join(team)
		.on(contract.team == team.name)
		.select(
			contract.name.as_("contract"),
			contract.currency,
			team.partner_email,
			team.user.as_("customer_email"),
			team.billing_name.as_("customer_name"),
			payment.period_start,
			payment.amount,
		)
		.where(contract.status.isin(OPEN_STATUSES))
		.where(team.enabled == 1)
		.where(team.partner_email.isin(partner_emails))
		.where(payment.period_start >= add_months(month, 1 - MONTHS_IN_YEAR))
		.where(payment.period_start <= get_last_day(month))
	).run(as_dict=True)
	for row in rows:
		row.amount = monthly_amount(row.amount, month_diff(month, row.period_start))
	return rows


# The last month takes the rounding difference, so the 12 shares add up to the payment.
def monthly_amount(amount: float, number: int) -> float:
	share = flt(amount / MONTHS_IN_YEAR, 2)
	return flt(amount - share * (MONTHS_IN_YEAR - 1), 2) if number == MONTHS_IN_YEAR else share


def partner_transaction(share: frappe._dict, month) -> dict:
	month = getdate(month)
	return {
		"invoice_id": f"{share.contract}-{month:%Y-%m}",
		"invoice_amount": share.amount,
		"currency": share.currency,
		"due_date": get_date_str(get_last_day(month)),
		"partner_email": share.partner_email,
		"team": share.customer_email,
		# Already paid, so frappe.io records it as a completed transaction.
		"docstatus": 1,
		"transaction_type": TRANSACTION_TYPE,
	}


# Runs at 00:00, so only the run on the 1st can send a payment made on the last day of the month before.
# frappe.io updates by reference, so a failed day is retried by the next run in that month.
def send_partner_transactions():
	if not frappe.db.get_single_value("Press Settings", "send_contract_partner_transactions"):
		return
	partners = frappe.get_all("Team", {"enabled": 1, "erpnext_partner": 1}, pluck="partner_email")
	transactions = [
		partner_transaction(share, month)
		for month in months_to_send()
		for share in contract_shares(month, partners)
	]
	if transactions:
		post_transactions(transactions)


# Other days send only this month: resending a past month would double count after a partner change.
def months_to_send() -> list:
	run_date = getdate()
	return [add_months(run_date, -1), run_date] if run_date.day == 1 else [run_date]


def post_transactions(transactions: list[dict]):
	client = get_frappe_io_connection()
	response = client.session.post(
		f"{client.url}/api/method/{TRANSACTION_ENDPOINT}",
		headers=client.headers,
		data={"partner_fc_invoices": json.dumps(transactions)},
	)
	response.raise_for_status()


def convert_to_partner_currency(amount: float, currency: str, partner_currency: str) -> float:
	if currency == partner_currency:
		return amount
	return flt(amount / 83, 2) if partner_currency == "USD" else flt(amount * 83, 2)


def contract_contribution(partner_email: str, partner_currency: str, month) -> float:
	shares = contract_shares(month, [partner_email])
	return flt(
		sum(convert_to_partner_currency(row.amount, row.currency, partner_currency) for row in shares), 2
	)


def contract_contribution_rows(partner_email: str, partner_currency: str) -> list[dict]:
	return [
		{
			"due_date": get_last_day(today()),
			"customer_name": row.customer_name,
			"total_before_discount": row.amount,
			"currency": row.currency,
			"status": "Paid",
			"partner_total": convert_to_partner_currency(row.amount, row.currency, partner_currency),
		}
		for row in contract_shares(today(), [partner_email])
	]


def add_contract_shares_to_mrr(rows: list, partner_email: str, partner_currency: str, months: list) -> list:
	totals = {row.due_date: row.total_amount for row in rows}
	for month in months:
		if amount := contract_contribution(partner_email, partner_currency, month):
			due_date = getdate(get_last_day(month))
			totals[due_date] = flt(totals.get(due_date)) + amount
	ordered = sorted(totals.items(), reverse=True)[:12]
	return [{"due_date": due_date, "total_amount": amount} for due_date, amount in ordered]
