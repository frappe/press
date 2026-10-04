# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import date_diff, now_datetime

from press.press.doctype.site_adoption_snapshot.site_adoption_snapshot import (
	REASON_FIELDS,
	behind_reason,
	get_active_sites,
	get_blocked_sites,
	get_group_types,
	get_newest_benches,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	rows = get_rows(filters)
	return get_columns(), rows, None, get_chart(rows), get_summary(rows)


def get_rows(filters: frappe._dict) -> list[frappe._dict]:
	"""Sites not on the newest bench of their group, most behind first."""
	groups = [filters.release_group] if filters.release_group else None
	newest = get_newest_benches(groups)
	newest_names = {bench.name for bench in newest.values()}
	behind = [
		site
		for site in get_active_sites(groups)
		if site.bench not in newest_names and (not filters.server or site.server == filters.server)
	]
	blocked = get_blocked_sites([site.name for site in behind])

	rows = []
	for site in behind:
		target = newest.get((site.group, site.server))
		rows.append(
			frappe._dict(
				site=site.name,
				release_group=site.group,
				server=site.server,
				bench=site.bench,
				is_standby=site.is_standby,
				reason=behind_reason(site, blocked),
				behind_since=target.creation if target else None,
				days_behind=date_diff(now_datetime(), target.creation) if target else None,
			)
		)

	set_group_types(rows)
	rows = [row for row in rows if matches(row, filters)]
	return sorted(rows, key=lambda row: row.days_behind or 0, reverse=True)


def set_group_types(rows: list[frappe._dict]):
	group_types = get_group_types(list({row.release_group for row in rows}))
	for row in rows:
		row.group_type = group_types.get(row.release_group, "Private")


def matches(row: frappe._dict, filters: frappe._dict) -> bool:
	if filters.group_type and row.group_type != filters.group_type:
		return False
	return not filters.reason or row.reason == filters.reason


def get_columns() -> list[dict]:
	return [
		{"fieldname": "site", "label": "Site", "fieldtype": "Link", "options": "Site", "width": 220},
		{"fieldname": "reason", "label": "Reason", "fieldtype": "Data", "width": 150},
		{"fieldname": "days_behind", "label": "Days Behind", "fieldtype": "Int", "width": 100},
		{"fieldname": "behind_since", "label": "Behind Since", "fieldtype": "Datetime", "width": 160},
		{"fieldname": "is_standby", "label": "Standby", "fieldtype": "Check", "width": 80},
		{"fieldname": "group_type", "label": "Group Type", "fieldtype": "Data", "width": 100},
		{
			"fieldname": "release_group",
			"label": "Release Group",
			"fieldtype": "Link",
			"options": "Release Group",
			"width": 140,
		},
		{"fieldname": "server", "label": "Server", "fieldtype": "Link", "options": "Server", "width": 200},
		{"fieldname": "bench", "label": "Bench", "fieldtype": "Link", "options": "Bench", "width": 180},
	]


def count_by_reason(rows: list[frappe._dict]) -> dict[str, int]:
	counts = dict.fromkeys(REASON_FIELDS, 0)
	for row in rows:
		counts[row.reason] += 1
	return counts


def get_chart(rows: list[frappe._dict]) -> dict:
	counts = count_by_reason(rows)
	return {
		"data": {
			"labels": list(counts),
			"datasets": [{"name": "Sites Behind", "values": list(counts.values())}],
		},
		"type": "bar",
	}


def get_summary(rows: list[frappe._dict]) -> list[dict]:
	counts = count_by_reason(rows)
	summary = [{"value": len(rows), "label": "Sites Behind", "datatype": "Int", "indicator": "orange"}]
	summary += [
		{
			"value": count,
			"label": reason,
			"datatype": "Int",
			"indicator": "blue" if reason == "Waiting" else "red",
		}
		for reason, count in counts.items()
		if count
	]
	return summary
