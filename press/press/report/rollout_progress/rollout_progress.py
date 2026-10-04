# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.utils import get_datetime

from press.press.doctype.site_adoption_snapshot.site_adoption_snapshot import ACTIVE_SITE_STATUSES
from press.press.report.adoption_overview.adoption_overview import percent


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.deploy_candidate:
		return get_columns(), []
	rows = get_rows(filters.deploy_candidate)
	return get_columns(), rows, None, get_chart(filters.deploy_candidate), get_summary(rows)


def get_rows(candidate: str) -> list[frappe._dict]:
	"""One row per server: the candidate's bench there, and the sites on it and still behind it."""
	group = frappe.db.get_value("Deploy Candidate", candidate, "group")
	moves = count_moves_by_server(candidate)
	rows = []
	for bench in get_candidate_benches(candidate):
		on_bench = count_sites({"bench": bench.name})
		# Sites can only move to an active bench, so nothing counts as behind one that is not
		behind = count_sites({"bench": ("in", get_older_benches(group, bench))}) if is_active(bench) else None
		rows.append(
			frappe._dict(
				server=bench.server,
				bench=bench.name,
				bench_status=bench.status,
				bench_created=bench.creation,
				moved=moves.get(bench.server, 0),
				on_bench=on_bench,
				behind=behind,
				percent_on_bench=percent(on_bench, on_bench + behind) if behind is not None else None,
			)
		)
	return rows


def get_candidate_benches(candidate: str) -> list[frappe._dict]:
	benches = frappe.get_all(
		"Bench",
		{"candidate": candidate, "status": ("!=", "Archived")},
		["name", "server", "status", "creation"],
		order_by="creation desc",
	)
	# Newest first, but an active bench wins over a newer one still installing or broken
	chosen: dict[str, frappe._dict] = {}
	for bench in benches:
		current = chosen.get(bench.server)
		if not current or (is_active(bench) and not is_active(current)):
			chosen[bench.server] = bench
	return sorted(chosen.values(), key=lambda bench: bench.server)


def is_active(bench: frappe._dict) -> bool:
	return bench.status == "Active"


def get_older_benches(group: str, bench: frappe._dict) -> list[str]:
	"""Benches of the group on the same server that came before this one."""
	return frappe.get_all(
		"Bench",
		{
			"group": group,
			"server": bench.server,
			"status": ("!=", "Archived"),
			"creation": ("<", bench.creation),
		},
		pluck="name",
	) or [""]


def count_sites(filters: dict) -> int:
	return frappe.db.count("Site", {"status": ("in", ACTIVE_SITE_STATUSES), **filters})


def get_moves(candidate: str) -> list[frappe._dict]:
	"""Site updates that moved a site onto the candidate, with when the move finished."""
	moves = frappe.get_all(
		"Site Update",
		{"destination_candidate": candidate, "status": "Success"},
		["server", "update_end", "update_start", "modified"],
	)
	for move in moves:
		move.moved_at = get_datetime(move.update_end or move.update_start or move.modified)
	return moves


def count_moves_by_server(candidate: str) -> dict[str, int]:
	counts: dict[str, int] = {}
	for move in get_moves(candidate):
		counts[move.server] = counts.get(move.server, 0) + 1
	return counts


def get_chart(candidate: str) -> dict:
	"""Sites moved onto the candidate, added up hour by hour."""
	per_hour: dict[str, int] = {}
	for move in get_moves(candidate):
		hour = move.moved_at.strftime("%Y-%m-%d %H:00")
		per_hour[hour] = per_hour.get(hour, 0) + 1

	labels = sorted(per_hour)
	values, total = [], 0
	for label in labels:
		total += per_hour[label]
		values.append(total)
	return {
		"data": {"labels": labels, "datasets": [{"name": "Sites Moved", "values": values}]},
		"type": "line",
	}


def get_columns() -> list[dict]:
	return [
		{"fieldname": "server", "label": "Server", "fieldtype": "Link", "options": "Server", "width": 200},
		{"fieldname": "bench", "label": "Bench", "fieldtype": "Link", "options": "Bench", "width": 180},
		{"fieldname": "bench_status", "label": "Bench Status", "fieldtype": "Data", "width": 110},
		{"fieldname": "bench_created", "label": "Bench Created", "fieldtype": "Datetime", "width": 160},
		{"fieldname": "percent_on_bench", "label": "% On Bench", "fieldtype": "Percent", "width": 110},
		{"fieldname": "on_bench", "label": "Sites On Bench", "fieldtype": "Int", "width": 120},
		{"fieldname": "behind", "label": "Sites Behind", "fieldtype": "Int", "width": 110},
		{"fieldname": "moved", "label": "Moved By Updates", "fieldtype": "Int", "width": 130},
	]


def get_summary(rows: list[frappe._dict]) -> list[dict]:
	active_rows = [row for row in rows if row.behind is not None]
	on_bench = sum(row.on_bench for row in active_rows)
	behind = sum(row.behind for row in active_rows)
	active = len(active_rows)
	return [
		{
			"value": percent(on_bench, on_bench + behind),
			"label": "% On This Deploy",
			"datatype": "Percent",
			"indicator": "green",
		},
		{"value": behind, "label": "Sites Behind", "datatype": "Int", "indicator": "orange"},
		{
			"value": sum(row.moved for row in rows),
			"label": "Moved By Updates",
			"datatype": "Int",
			"indicator": "blue",
		},
		{
			"value": f"{active} / {len(rows)}",
			"label": "Benches Active",
			"datatype": "Data",
			"indicator": "blue",
		},
	]
