# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Settle a team's open invoices with its credit, then move what is left to another team."""

from __future__ import annotations

import frappe
from frappe.utils import flt

from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.team.team import Team


def settle_open_invoices(team: str):
	"""Pay the unpaid invoices, then the current invoice, from credit alone. No payment gateway is charged."""
	for status in ("Unpaid", "Draft"):
		for invoice in open_invoices(team, status):
			settle_with_credit(invoice)


def open_invoices(team: str, status: str) -> list[Invoice]:
	# Stripe collects an invoice it already has; paying it from credit too can charge twice
	names = frappe.get_all(
		"Invoice",
		{
			"team": team,
			"status": status,
			"type": "Subscription",
			"docstatus": 0,
			"stripe_invoice_id": ("is", "not set"),
		},
		pluck="name",
		order_by="period_start asc",
	)
	return [Invoice("Invoice", name) for name in names]


def settle_with_credit(invoice: Invoice):
	"""Close the invoice today if credit covers it. A shortfall stays on it for the scheduled billing."""
	invoice.apply_partner_discounts()
	invoice.calculate_values()
	if invoice.amount_due > 0:
		invoice.apply_credit_balance()
	if invoice.amount_due > 0:
		# Leave it open with the credit applied; a Draft keeps its period_end so the monthly finalize still bills it
		invoice.save()
		return
	close_paid_invoice(invoice)


def close_paid_invoice(invoice: Invoice):
	invoice.status = "Empty" if invoice.total == 0 else "Paid"
	invoice.truncate_period_end_if_finalized_early()
	invoice.update_item_descriptions()
	invoice.submit()
	if invoice.status == "Paid":
		invoice.unsuspend_sites_if_applicable()
	invoice.ensure_next_invoice_exists()


def move_balance(from_team: str, to_team: str, exchange_rate: float, remark: str) -> float:
	"""Credit `to_team` per source, then debit `from_team` once. Returns the amount taken from `from_team`."""
	credit_by_source = unallocated_credit_by_source(from_team)
	total = sum(credit_by_source.values())
	if total <= 0:
		return 0

	receiving_team = Team("Team", to_team)
	for source, amount in credit_by_source.items():
		receiving_team.allocate_credit_amount(flt(amount * exchange_rate, 2), source, remark)
	Team("Team", from_team).allocate_credit_amount(-total, "Transferred Credits", remark)
	return total


def unallocated_credit_by_source(team: str) -> dict[str, float]:
	credits = frappe.get_all(
		"Balance Transaction",
		filters={"team": team, "docstatus": 1, "unallocated_amount": (">", 0)},
		fields=["source", "unallocated_amount"],
	)
	credit_by_source: dict[str, float] = {}
	for credit in credits:
		credit_by_source[credit.source] = credit_by_source.get(credit.source, 0) + credit.unallocated_amount
	return credit_by_source
