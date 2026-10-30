# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Spread each yearly contract payment over 12 monthly invoice lines that the contract
pays, so they count for partner contribution but never draw on team credits."""

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.utils import add_months, flt, get_first_day, get_last_day, getdate

if TYPE_CHECKING:
	from press.press.doctype.invoice.invoice import Invoice

INSTALLMENTS = 12
OPEN_STATUSES = ("Pending Signature", "Active")


def add_installment(invoice: Invoice):
	if invoice.type != "Subscription" or has_installment(invoice):
		return
	month = get_first_day(invoice.period_start)
	payment = payment_covering(invoice.team, month)
	if not payment or billed_in_month(payment.contract, month):
		return
	number = months_between(get_first_day(payment.period_start), month) + 1
	invoice.append(
		"items",
		{
			"description": f"Enterprise Warranty ({payment.contract}), month {number} of {INSTALLMENTS}",
			"document_type": "Enterprise Contract",
			"document_name": payment.contract,
			"quantity": 1,
			"rate": installment_amount(payment.amount, number),
			"discount": 0,
		},
	)


def add_installment_to_current_invoice(team: str):
	name = frappe.db.get_value(
		"Invoice",
		{"team": team, "type": "Subscription", "docstatus": 0, "period_end": (">=", getdate())},
		"name",
		order_by="period_start asc",
	)
	if not name:
		# The new invoice adds this month's line in before_insert.
		frappe.get_doc("Team", team).create_upcoming_invoice()
		return
	invoice = frappe.get_doc("Invoice", name)
	add_installment(invoice)
	# Recorded on behalf of the team; callers check billing access.
	invoice.save(ignore_permissions=True)


def has_installment(invoice: Invoice) -> bool:
	return any(item.document_type == "Enterprise Contract" for item in invoice.items)


# An invoice finalized early is followed by one starting mid-month; the month is billed once.
def billed_in_month(contract: str, month) -> bool:
	item = frappe.qb.DocType("Invoice Item")
	invoice = frappe.qb.DocType("Invoice")
	rows = (
		frappe.qb.from_(item)
		.join(invoice)
		.on(item.parent == invoice.name)
		.select(item.name)
		.where(item.parenttype == "Invoice")
		.where(item.document_type == "Enterprise Contract")
		.where(item.document_name == contract)
		.where(invoice.docstatus < 2)
		.where(invoice.period_start[get_first_day(month) : get_last_day(month)])
		.limit(1)
	).run()
	return bool(rows)


def paid_by_contract(invoice: Invoice) -> float:
	return flt(sum(item.amount for item in invoice.items if item.document_type == "Enterprise Contract"), 2)


# The contract line is in the invoice total, but it was prepaid, so it is not monthly spend.
def usage_total(invoice) -> float:
	return flt(flt(invoice.total) - flt(invoice.paid_by_contract), 2) if invoice else 0


def payment_covering(team: str, month) -> frappe._dict | None:
	payment = frappe.qb.DocType("Enterprise Contract Payment")
	contract = frappe.qb.DocType("Enterprise Contract")
	rows = (
		frappe.qb.from_(payment)
		.join(contract)
		.on(payment.parent == contract.name)
		.select(contract.name.as_("contract"), payment.period_start, payment.amount)
		.where(contract.team == team)
		.where(contract.status.isin(OPEN_STATUSES))
		.where(payment.period_start >= add_months(month, 1 - INSTALLMENTS))
		.where(payment.period_start <= get_last_day(month))
		.limit(1)
	).run(as_dict=True)
	return rows[0] if rows else None


# The last month takes the rounding difference, so the 12 lines add up to the payment.
def installment_amount(amount: float, number: int) -> float:
	share = flt(amount / INSTALLMENTS, 2)
	return flt(amount - share * (INSTALLMENTS - 1), 2) if number == INSTALLMENTS else share


def months_between(start, end) -> int:
	start, end = getdate(start), getdate(end)
	return (end.year - start.year) * 12 + end.month - start.month
