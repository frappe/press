# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import add_days, flt, get_datetime, getdate, today

from press.press.doctype.site_adoption_snapshot.site_adoption_snapshot import COUNT_FIELDS, REASON_FIELDS


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = get_rows(filters)
	return get_columns(filters), rows, None, get_chart(rows), get_summary(rows)


def get_rows(filters: frappe._dict) -> list[frappe._dict]:
	"""Daily rows by group type, or the hourly rows of one group when a group is picked."""
	from_date = getdate(filters.from_date or add_days(today(), -30))
	to_date = getdate(filters.to_date or today())
	conditions: dict[str, Any] = {
		"timestamp": ("between", [get_datetime(from_date), get_datetime(add_days(to_date, 1))])
	}
	if filters.release_group:
		conditions.update(tier="Hourly", release_group=filters.release_group)
	else:
		conditions["tier"] = "Daily"

	rows = frappe.get_all(
		"Site Adoption Snapshot",
		conditions,
		["timestamp", "group_type", "release_group", *COUNT_FIELDS],
		order_by="timestamp asc, group_type asc",
	)
	for row in rows:
		row.percent_current = percent(row.current_sites, row.current_sites + row.behind_sites)
	return rows


def percent(part: int, whole: int) -> float:
	return flt(100 * part / whole, 1) if whole else 0.0


def get_columns(filters: frappe._dict) -> list[dict]:
	columns = [
		{"fieldname": "timestamp", "label": "Timestamp", "fieldtype": "Datetime", "width": 160},
		{"fieldname": "group_type", "label": "Group Type", "fieldtype": "Data", "width": 100},
	]
	if filters.release_group:
		columns.append(
			{
				"fieldname": "release_group",
				"label": "Release Group",
				"fieldtype": "Link",
				"options": "Release Group",
				"width": 140,
			}
		)
	columns += [
		{"fieldname": "percent_current", "label": "% Current", "fieldtype": "Percent", "width": 100},
		{"fieldname": "current_sites", "label": "Current", "fieldtype": "Int", "width": 90},
		{"fieldname": "behind_sites", "label": "Behind", "fieldtype": "Int", "width": 90},
		{"fieldname": "standby_behind", "label": "Standby Behind", "fieldtype": "Int", "width": 120},
		{"fieldname": "old_benches", "label": "Old Benches", "fieldtype": "Int", "width": 110},
	]
	columns += [
		{"fieldname": field, "label": label, "fieldtype": "Int", "width": 120}
		for label, field in REASON_FIELDS.items()
	]
	return columns


def get_chart(rows: list[frappe._dict]) -> dict:
	"""% current over time, one line per group type."""
	labels = sorted({str(row.timestamp) for row in rows})
	by_type: dict[str, dict[str, float]] = {}
	for row in rows:
		by_type.setdefault(row.group_type, {})[str(row.timestamp)] = row.percent_current

	datasets = [
		{"name": group_type, "values": [values.get(label, 0) for label in labels]}
		for group_type, values in by_type.items()
	]
	return {"data": {"labels": labels, "datasets": datasets}, "type": "line"}


def get_summary(rows: list[frappe._dict]) -> list[dict]:
	"""Headline numbers from the latest snapshot in the range."""
	if not rows:
		return []
	latest = [row for row in rows if row.timestamp == rows[-1].timestamp]
	current = sum(row.current_sites for row in latest)
	behind = sum(row.behind_sites for row in latest)
	return [
		{
			"value": percent(current, current + behind),
			"label": "% Current",
			"datatype": "Percent",
			"indicator": "green",
		},
		{"value": behind, "label": "Sites Behind", "datatype": "Int", "indicator": "orange"},
		{
			"value": sum(row.waiting for row in latest),
			"label": "Waiting To Move",
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": behind - sum(row.waiting for row in latest),
			"label": "Blocked",
			"datatype": "Int",
			"indicator": "red",
		},
		{
			"value": sum(row.old_benches for row in latest),
			"label": "Old Benches",
			"datatype": "Int",
			"indicator": "orange",
		},
	]
