from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any

import frappe

RECENT_LIMIT = 10
_SPIKE_CPU_THRESHOLD = 70.0  # flag CPU spike only above this percent
_SPIKE_RATIO = 1.5  # peak must be this many times the mean to count as a spike
_IOPS_SPIKE_RATIO = 2.0  # IOPS has no useful absolute threshold; rely on ratio only
_SLOW_ENDPOINT_THRESHOLD_S = 1.0  # average duration above which an endpoint is worth flagging
_PERF_SPIKE_PEAK_THRESHOLD_S = 2.0  # peak must exceed this to register as a performance spike
_PERF_SPIKE_RATIO = 3.0  # peak must be this many times the mean to count as a spike
_PERF_MAX_PATHS = 20  # fetch up to this many endpoints for anomaly analysis
_WEB_ERROR_TAIL_LINES = 500  # scan only the tail of the log to bound processing time
_WEB_ERROR_MAX_ERRORS = 10  # return at most this many recent error blocks
_WEB_ERROR_LOG_REGEX = re.compile(
	r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4})\] \[(\d+)\] \[(\w+)\] (.*)"
)


def collect_site_context(site_name: str) -> dict[str, Any]:
	site = _get_site(site_name)
	bench = get_bench_health(site.get("bench"))
	db_server = bench.get("database_server") if bench else None

	app_server_metrics = get_server_metrics(site.get("server"))
	db_server_metrics = get_server_metrics(db_server, is_db_server=True)

	server_advanced_analytics = (
		get_server_advanced_analytics(site.get("server"), site_name)
		if _any_spike(app_server_metrics, db_server_metrics)
		else None
	)

	return {
		"site": get_site_health(site),
		"bench": bench,
		"apps": get_app_versions(site.get("bench")),
		"deployments": get_deployment_timeline(site_name),
		"background_jobs": get_background_job_summary(site_name),
		"backups": get_backup_status(site_name),
		"domains": get_domain_status(site_name),
		"incidents": get_platform_incidents(site),
		"errors": get_redacted_error_summary(site_name),
		"app_server_metrics": app_server_metrics,
		"db_server_metrics": db_server_metrics,
		"server_advanced_analytics": server_advanced_analytics,
		"site_performance": get_site_performance_summary(site_name, site.get("bench")),
		"web_error_log": get_web_error_log(site_name),
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


def get_server_metrics(server_name: str | None, is_db_server: bool = False) -> dict[str, Any] | None:
	if not server_name:
		return None

	if not frappe.db.get_single_value("Press Settings", "monitor_server"):
		return {"available": False}

	from press.api.server import prometheus_query

	timespan = 24 * 60 * 60
	timegrain = 30 * 60

	try:
		cpu_data = prometheus_query(
			f'(1 - avg(rate(node_cpu_seconds_total{{instance="{server_name}",job="node",mode="idle"}}[{timegrain}s]))) * 100',
			lambda _: "cpu",
			"UTC",
			timespan,
			timegrain,
		)
	except Exception:
		return {"available": False}

	result: dict[str, Any] = {
		"available": True,
		"cpu": _summarise_series(cpu_data, absolute_threshold=_SPIKE_CPU_THRESHOLD),
	}

	if is_db_server:
		try:
			iops_data = prometheus_query(
				f'sum(rate(node_disk_reads_completed_total{{instance="{server_name}",job="node"}}[{timegrain}s]) + rate(node_disk_writes_completed_total{{instance="{server_name}",job="node"}}[{timegrain}s]))',
				lambda _: "iops",
				"UTC",
				timespan,
				timegrain,
			)
			result["iops"] = _summarise_series(iops_data, ratio_threshold=_IOPS_SPIKE_RATIO)
		except Exception:
			result["iops"] = {"available": False}

	return result


def get_server_advanced_analytics(server_name: str | None, target_site: str) -> dict[str, Any] | None:
	"""
	Returns anonymized per-tenant CPU share on the app server.
	Site names are never included — only the target site's rank and share are returned.
	Used to detect noisy neighbors when a server CPU spike is observed.
	"""
	if not server_name:
		return None

	from press.api.analytics import get_current_cpu_usage_for_sites_on_server

	usage_by_site = get_current_cpu_usage_for_sites_on_server(server_name)
	if not usage_by_site:
		return {"available": False}

	total = sum(usage_by_site.values())
	if not total:
		return {"available": False}

	sorted_entries = sorted(usage_by_site.items(), key=lambda x: x[1], reverse=True)
	site_names = [name for name, _ in sorted_entries]

	target_rank = site_names.index(target_site) + 1 if target_site in site_names else None
	target_share = round(usage_by_site.get(target_site, 0) / total * 100, 1)
	top_5_shares = [round(v / total * 100, 1) for _, v in sorted_entries[:5]]

	return {
		"available": True,
		"site_count": len(usage_by_site),
		"target_site_rank": target_rank,
		"target_site_share_percent": target_share,
		"top_5_shares_percent": top_5_shares,
	}


def get_site_performance_summary(site_name: str, bench_name: str | None = None) -> dict[str, Any]:
	"""
	Slowest endpoints from Elasticsearch for the last 24 hours with anomaly detection.

	Each endpoint records avg/peak duration, whether a spike was detected
	(peak >= _PERF_SPIKE_RATIO x mean and peak > _PERF_SPIKE_PEAK_THRESHOLD_S), and
	whether the endpoint belongs to a non-Frappe app installed on the bench.
	"""
	if not frappe.db.get_single_value("Press Settings", "log_server"):
		return {"available": False}

	from press.api.analytics import AggType, ResourceType, auto_timespan_timegrain, get_request_by_

	end_dt = datetime.now(tz=dt_timezone.utc)
	start_dt = end_dt - timedelta(hours=24)
	timespan, timegrain = auto_timespan_timegrain(start_dt, end_dt)

	try:
		result = get_request_by_(
			site_name,
			AggType.AVERAGE_DURATION,
			"UTC",
			start_dt,
			end_dt,
			timespan,
			timegrain,
			ResourceType.SITE,
			max_no_of_paths=_PERF_MAX_PATHS,
		)
	except Exception:
		return {"available": False}

	custom_apps = _get_custom_app_names(bench_name)

	endpoints = []
	for ds in result.get("datasets") or []:
		values = [v for v in (ds.get("values") or []) if v is not None]
		if not values:
			continue
		avg = round(sum(values) / len(values), 3)
		peak = round(max(values), 3)
		spike_detected = peak >= _PERF_SPIKE_PEAK_THRESHOLD_S and avg > 0 and peak >= avg * _PERF_SPIKE_RATIO
		path = ds.get("path") or ""
		module = _endpoint_module(path)
		endpoints.append(
			{
				"path": path,
				"avg_duration_s": avg,
				"peak_duration_s": peak,
				"spike_detected": spike_detected,
				"is_custom": module is not None and module in custom_apps,
			}
		)

	endpoints.sort(key=lambda x: x["avg_duration_s"], reverse=True)
	return {
		"available": True,
		"has_custom_apps": bool(custom_apps),
		"top_slow_endpoints": endpoints[:10],
	}


def _get_custom_app_names(bench_name: str | None) -> set[str]:
	"""Returns the Python package names of apps whose source is not in the frappe GitHub org."""
	if not bench_name:
		return set()

	bench_apps = frappe.get_all(
		"Bench App",
		filters={"parenttype": "Bench", "parent": bench_name},
		fields=["app", "source"],
	)
	if not bench_apps:
		return set()

	source_names = [a.source for a in bench_apps if a.source]
	if not source_names:
		return set()

	sources = frappe.get_all(
		"App Source",
		filters={"name": ("in", source_names)},
		fields=["name", "repository_owner"],
	)
	owner_by_source = {s.name: (s.repository_owner or "").lower() for s in sources}

	return {a.app for a in bench_apps if owner_by_source.get(a.source, "") != "frappe"}


def _endpoint_module(path: str) -> str | None:
	"""Extracts the Python module name from /api/method/<module>.<rest> paths."""
	prefix = "/api/method/"
	if not path.startswith(prefix):
		return None
	rest = path[len(prefix) :]
	return rest.split(".")[0] or None


def get_web_error_log(site_name: str) -> dict[str, Any]:
	"""
	Recent ERROR/CRITICAL entries from web.error.log, redacted.

	Only the exception message line (last line of the traceback) is included —
	not full stack frames with local variables. All entries pass through redact()
	before being stored.
	"""
	from press.incident_management.support_agent.redaction import redact

	try:
		raw = frappe.get_doc("Site", site_name).get_server_log("web.error.log")
	except Exception:
		return {"available": False}

	content = (raw or {}).get("web.error.log", "")
	if not content:
		return {"available": True, "error_count": 0, "recent_errors": []}

	lines = content.strip().splitlines()
	error_blocks = _parse_web_error_blocks(lines[-_WEB_ERROR_TAIL_LINES:])
	return {
		"available": True,
		"error_count": len(error_blocks),
		"recent_errors": redact(error_blocks[-_WEB_ERROR_MAX_ERRORS:]),
	}


def _parse_web_error_blocks(lines: list[str]) -> list[dict[str, Any]]:
	"""
	Parses gunicorn web.error.log lines into typed error blocks.

	Each block is a dict with: time, level, description, and optionally exception
	(the last line of the associated traceback — the exception class and message).
	Only ERROR and CRITICAL level blocks are returned.
	"""
	blocks = []
	current: dict[str, Any] | None = None
	traceback_lines: list[str] = []

	for line in lines:
		match = _WEB_ERROR_LOG_REGEX.match(line)
		if match:
			if current is not None and current["level"] in ("error", "critical"):
				if traceback_lines:
					current["exception"] = traceback_lines[-1].strip()
				blocks.append(current)
			timestamp, _pid, level, description = match.groups()
			current = {"time": timestamp, "level": level.lower(), "description": description}
			traceback_lines = []
		elif current is not None:
			traceback_lines.append(line)

	if current is not None and current["level"] in ("error", "critical"):
		if traceback_lines:
			current["exception"] = traceback_lines[-1].strip()
		blocks.append(current)

	return blocks


def _summarise_series(
	data: dict[str, Any],
	absolute_threshold: float | None = None,
	ratio_threshold: float = _SPIKE_RATIO,
) -> dict[str, Any]:
	datasets = data.get("datasets") or []
	all_values = [v for ds in datasets for v in (ds.get("values") or []) if v is not None]
	if not all_values:
		return {"available": False, "peak": None, "mean": None, "spike_detected": False}

	peak = max(all_values)
	mean = sum(all_values) / len(all_values)
	above_threshold = absolute_threshold is None or peak >= absolute_threshold
	spike_detected = above_threshold and mean > 0 and peak >= mean * ratio_threshold

	return {
		"available": True,
		"peak": round(peak, 1),
		"mean": round(mean, 1),
		"spike_detected": spike_detected,
	}


def _any_spike(app_metrics: dict[str, Any] | None, db_metrics: dict[str, Any] | None) -> bool:
	if app_metrics and app_metrics.get("cpu", {}).get("spike_detected"):
		return True
	if db_metrics:
		if db_metrics.get("cpu", {}).get("spike_detected"):
			return True
		if db_metrics.get("iops", {}).get("spike_detected"):
			return True
	return False


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
