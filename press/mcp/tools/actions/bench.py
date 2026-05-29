# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.utils import system_manager_only

_CANCEL_STUCK_JOBS_LIMIT = 50


@press_mcp.tool()
@system_manager_only
def restart_bench(bench: str, confirm: bool = False) -> dict:
	"""Restart gunicorn and workers for a bench.

	Causes brief downtime (seconds) while processes restart. All sites on
	the bench are affected. Common fix for hung workers or memory leaks.

	Pass confirm=True to execute. Without it, returns a dry-run summary.
	"""
	if not frappe.db.exists("Bench", bench):
		frappe.throw(f"Bench {bench!r} not found")

	if not confirm:
		bench_doc = frappe.get_doc("Bench", bench)
		site_count = frappe.db.count("Site", {"bench": bench, "status": "Active"})
		return {
			"action": "restart_bench",
			"bench": bench,
			"group": bench_doc.group,
			"active_sites_affected": site_count,
			"impact": "Restarts gunicorn and workers. Brief downtime for all sites on this bench.",
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	frappe.get_doc("Bench", bench).restart()
	return {"action": "restart_bench", "bench": bench, "status": "triggered"}


@press_mcp.tool()
@system_manager_only
def cancel_stuck_jobs(bench: str, confirm: bool = False) -> dict:
	"""Cancel agent jobs stuck in Running state on a bench.

	Targets jobs that are Running on this bench and are typically safe
	to cancel: Backup Site, Restore Site, Fetch Database Table Schema.
	These commonly get stuck during a database reboot or upgrade.

	For broader incident-level job management (all job types, incident
	scope), use the Incident document's cancel_stuck_jobs action directly.

	Pass confirm=True to execute. Without it, lists jobs that would be cancelled.
	"""
	if not frappe.db.exists("Bench", bench):
		frappe.throw(f"Bench {bench!r} not found")

	cancellable_job_types = [
		"Backup Site",
		"Restore Site",
		"Fetch Database Table Schema",
	]

	stuck_jobs = frappe.get_all(
		"Agent Job",
		filters={
			"bench": bench,
			"status": "Running",
			"job_type": ("in", cancellable_job_types),
		},
		fields=["name", "job_type", "site", "creation"],
		order_by="creation asc",
		limit=_CANCEL_STUCK_JOBS_LIMIT,
	)

	if not stuck_jobs:
		return {
			"action": "cancel_stuck_jobs",
			"bench": bench,
			"stuck_jobs": [],
			"note": "No stuck jobs found.",
		}

	if not confirm:
		return {
			"action": "cancel_stuck_jobs",
			"bench": bench,
			"stuck_jobs": stuck_jobs,
			"impact": f"Will cancel up to {_CANCEL_STUCK_JOBS_LIMIT} stuck job(s) in this request.",
			"limit": _CANCEL_STUCK_JOBS_LIMIT,
			"requires_confirm": True,
			"next_step": "Call again with confirm=True to execute.",
		}

	cancelled = []
	for job in stuck_jobs:
		frappe.get_doc("Agent Job", job.name).cancel_job()
		cancelled.append({"name": job.name, "job_type": job.job_type, "site": job.site})

	return {
		"action": "cancel_stuck_jobs",
		"bench": bench,
		"cancelled": cancelled,
		"limit": _CANCEL_STUCK_JOBS_LIMIT,
		"status": "triggered",
	}
