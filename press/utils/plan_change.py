# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe

PLAN_FIELDS = ("from_plan", "to_plan")


def snapshot_plans(doc, plan_doctype: str, fields: tuple[str, ...]) -> None:
	"""Record what each plan held when the change was made.

	The dashboard shows the price and the resources of both plans. A plan can be
	edited after the change, so reading the plan later would rewrite the history.
	The values are copied onto the change instead.
	"""
	for field in PLAN_FIELDS:
		plan = doc.get(field)
		snapshot = read_plan(plan_doctype, plan, fields) if plan else None
		doc.set(f"{field}_snapshot", snapshot)


def read_plan(plan_doctype: str, plan: str, fields: tuple[str, ...]) -> dict | None:
	return frappe.db.get_value(plan_doctype, plan, ["name", *fields], as_dict=True)


def attach_plan_details(rows: list[dict], doctype: str, plan_doctype: str, fields: tuple[str, ...]) -> None:
	"""Put the plans a plan change points at on the plan change row itself.

	Each row carries what its plans held at the time of the change. A row written
	before those snapshots existed has none, so its plans are read as they stand
	today. That is the best the old rows allow.
	"""
	snapshots = read_snapshots(doctype, rows)
	plan_by_name = read_missing_plans(rows, snapshots, plan_doctype, fields)

	for row in rows:
		snapshot = snapshots.get(str(row.get("name")), {})
		for field in PLAN_FIELDS:
			row[f"{field}_details"] = snapshot.get(field) or plan_by_name.get(str(row.get(field)))


def read_snapshots(doctype: str, rows: list[dict]) -> dict[str, dict]:
	names = {row.get("name") for row in rows}
	names.discard(None)
	if not names:
		return {}

	snapshot_fields = [f"{field}_snapshot" for field in PLAN_FIELDS]
	stored = frappe.get_all(doctype, filters={"name": ("in", list(names))}, fields=["name", *snapshot_fields])
	return {row.name: {field: parse(row.get(f"{field}_snapshot")) for field in PLAN_FIELDS} for row in stored}


def parse(snapshot: str | dict | None) -> dict | None:
	if not snapshot:
		return None
	if isinstance(snapshot, dict):
		return snapshot

	try:
		return json.loads(snapshot)
	except ValueError:
		return None


def read_missing_plans(
	rows: list[dict], snapshots: dict[str, dict], plan_doctype: str, fields: tuple[str, ...]
) -> dict[str, dict]:
	"""Read the plans of the rows that carry no snapshot, in one query."""
	names: set[str | None] = set()
	for row in rows:
		snapshot = snapshots.get(str(row.get("name")), {})
		names.update(row.get(field) for field in PLAN_FIELDS if not snapshot.get(field))

	names.discard(None)
	names.discard("")
	if not names:
		return {}

	plans = frappe.get_all(plan_doctype, filters={"name": ("in", list(names))}, fields=["name", *fields])
	return {plan.name: plan for plan in plans}
