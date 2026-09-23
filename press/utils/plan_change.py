# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

PLAN_FIELDS = ("from_plan", "to_plan")


def attach_plan_details(rows: list[dict], plan_doctype: str, fields: tuple[str, ...]) -> None:
	"""Put the plans a plan change points at on the plan change row itself.

	The dashboard shows the price and the resources of a plan, not the plan name,
	so each row needs both plan documents. A list query cannot join the same
	doctype twice, which is what `from_plan` and `to_plan` ask for, so the plans
	are read here and set as `from_plan_details` and `to_plan_details`.
	"""
	names = {row.get(field) for field in PLAN_FIELDS for row in rows}
	names.discard(None)
	names.discard("")
	if not names:
		return

	plans = frappe.get_all(plan_doctype, filters={"name": ("in", list(names))}, fields=["name", *fields])
	plan_by_name = {plan.name: plan for plan in plans}

	for row in rows:
		for field in PLAN_FIELDS:
			row[f"{field}_details"] = plan_by_name.get(row.get(field))
