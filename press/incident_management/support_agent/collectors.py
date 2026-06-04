from __future__ import annotations

from collections import Counter
from typing import Any

import frappe

RECENT_LIMIT = 10


def collect_site_context(site_name: str) -> dict[str, Any]:
	site = _get_site(site_name)
	return {
		"site": get_site_health(site),
		"bench": get_bench_health(site.get("bench")),
		"apps": get_app_versions(site.get("bench")),
		"deployments": get_deployment_timeline(site.name),
		"background_jobs": get_background_job_summary(site.name),
		"backups": get_backup_status(site.name),
		"domains": get_domain_status(site.name),
		"incidents": get_platform_incidents(site),
		"errors": get_redacted_error_summary(site.name),
	}


def get_site_health(site: frappe._dict) -> dict[str, Any]:
	return {
		"name": site.name,
		"status": site.status,
		"bench": site.bench,
		"server": site.server,
		"cluster": site.cluster,
		"group": site.group,
		"archive_failed": bool(site.archive_failed),
		"creation_failed": site.creation_failed,
		"suspended_at": site.suspended_at,
		"monitoring_disabled": bool(site.is_monitoring_disabled),
		"setup_wizard_complete": bool(site.setup_wizard_complete),
		"usage_percent": {
			"cpu": site.current_cpu_usage,
			"database": site.current_database_usage,
			"disk": site.current_disk_usage,
		},
	}


def get_bench_health(bench_name: str | None) -> dict[str, Any] | None:
	if not bench_name:
		return None

	return frappe.db.get_value(
		"Bench",
		bench_name,
		[
			"name",
			"status",
			"server",
			"database_server",
			"cluster",
			"candidate",
			"build",
			"background_workers",
			"gunicorn_workers",
			"auto_scale_workers",
			"use_rq_workerpool",
			"merge_all_rq_queues",
			"merge_default_and_short_rq_queues",
			"last_inplace_update_failed",
			"resetting_bench",
		],
		as_dict=True,
	)


def get_app_versions(bench_name: str | None) -> list[dict[str, Any]]:
	if not bench_name:
		return []

	return frappe.get_all(
		"Bench App",
		filters={"parenttype": "Bench", "parent": bench_name},
		fields=["app", "source", "release", "hash"],
		order_by="idx asc",
	)


def get_deployment_timeline(site_name: str) -> list[dict[str, Any]]:
	return frappe.get_all(
		"Site Update",
		filters={"site": site_name},
		fields=[
			"name",
			"creation",
			"status",
			"deploy_type",
			"scheduled_time",
			"update_start",
			"update_end",
			"update_duration",
			"source_bench",
			"destination_bench",
			"backup_type",
			"skipped_backups",
			"skipped_failing_patches",
		],
		order_by="creation desc",
		limit=5,
	)


def get_background_job_summary(site_name: str) -> dict[str, Any]:
	since = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-24)
	jobs = frappe.get_all(
		"Agent Job",
		filters={"site": site_name, "creation": (">", since)},
		fields=[
			"name",
			"creation",
			"job_type",
			"status",
			"start",
			"end",
			"duration",
			"retry_count",
			"next_retry_at",
			"reference_doctype",
		],
		order_by="creation desc",
		limit=RECENT_LIMIT,
	)

	return {
		"window_hours": 24,
		"counts_by_status": dict(Counter(job.status for job in jobs)),
		"recent": jobs,
	}


def get_backup_status(site_name: str) -> dict[str, Any]:
	backups = frappe.get_all(
		"Site Backup",
		filters={"site": site_name},
		fields=[
			"name",
			"creation",
			"status",
			"database_size",
			"public_size",
			"private_size",
			"with_files",
			"offsite",
			"physical",
			"files_availability",
		],
		order_by="creation desc",
		limit=5,
	)
	return {
		"latest": backups[0] if backups else None,
		"recent": backups,
		"counts_by_status": dict(Counter(backup.status for backup in backups)),
	}


def get_domain_status(site_name: str) -> dict[str, Any]:
	domains = frappe.get_all(
		"Site Domain",
		filters={"site": site_name},
		fields=["status", "dns_type", "redirect_to_primary"],
		limit=50,
	)
	return {
		"total": len(domains),
		"counts_by_status": dict(Counter(domain.status for domain in domains)),
		"records": domains,
	}


def get_platform_incidents(site: frappe._dict) -> list[dict[str, Any]]:
	filters = {
		"status": ("not in", ["Resolved", "Auto-Resolved", "Press-Resolved"]),
	}
	conditions = []
	if site.server:
		conditions.append(["server", "=", site.server])
	if site.cluster:
		conditions.append(["cluster", "=", site.cluster])

	if not conditions:
		return []

	return frappe.get_all(
		"Incident",
		filters=filters,
		or_filters=conditions,
		fields=["name", "creation", "status", "type", "subtype", "server", "cluster", "resource_type"],
		order_by="creation desc",
		limit=5,
	)


def get_redacted_error_summary(site_name: str) -> dict[str, Any]:
	since = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=-24)
	failed_jobs = frappe.get_all(
		"Agent Job",
		filters={
			"site": site_name,
			"status": ("in", ["Failure", "Delivery Failure"]),
			"creation": (">", since),
		},
		fields=["job_type", "reference_doctype", "retry_count", "creation"],
		order_by="creation desc",
		limit=50,
	)

	by_job_type = Counter(job.job_type for job in failed_jobs)
	return {
		"window_hours": 24,
		"failed_job_count": len(failed_jobs),
		"failed_jobs_by_type": dict(by_job_type),
		"recent_failed_jobs": failed_jobs[:RECENT_LIMIT],
	}


def _get_site(site_name: str) -> frappe._dict:
	return frappe.db.get_value(
		"Site",
		site_name,
		[
			"name",
			"status",
			"bench",
			"server",
			"cluster",
			"group",
			"archive_failed",
			"creation_failed",
			"suspended_at",
			"is_monitoring_disabled",
			"setup_wizard_complete",
			"current_cpu_usage",
			"current_database_usage",
			"current_disk_usage",
		],
		as_dict=True,
	)
