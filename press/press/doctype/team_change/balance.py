# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Settle a team's open invoices with its credit, then move what is left to another team."""

from __future__ import annotations

import frappe
from frappe.utils import flt

from press.press.doctype.invoice.invoice import Invoice
from press.press.doctype.team.team import Team, enqueue_finalize_unpaid_for_team


def settle_open_invoices(team: str):
	"""Pay unpaid invoices from credit, then close the current invoice today so credit pays it too"""
	enqueue_finalize_unpaid_for_team(team)
	drafts = frappe.get_all(
		"Invoice",
		{"team": team, "status": "Draft", "type": "Subscription", "docstatus": 0},
		pluck="name",
		order_by="period_start asc",
	)
	for draft in drafts:
		Invoice("Invoice", draft).finalize_invoice()


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
