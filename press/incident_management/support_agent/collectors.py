from __future__ import annotations

import math
import re
from collections import Counter
from typing import TYPE_CHECKING, Any

import frappe
from frappe.utils import get_system_timezone

from press.utils import convert_user_timezone_to_utc

if TYPE_CHECKING:
	from collections.abc import Iterable
	from datetime import datetime

RECENT_LIMIT = 10
_WINDOW_HALF_HOURS = 12  # investigation looks this far either side of the time of interest
_PROM_STEP = 30 * 60  # Prometheus step size in seconds
_SPIKE_CPU_THRESHOLD = 70.0  # flag CPU spike only above this percent
_SPIKE_RATIO = 1.5  # peak must be this many times the mean to count as a spike
_IOPS_SPIKE_RATIO = 2.0  # IOPS has no useful absolute threshold; rely on ratio only
_SLOW_ENDPOINT_THRESHOLD_S = 1.0  # average duration above which an endpoint is worth flagging
_PERF_SPIKE_PEAK_THRESHOLD_S = 2.0  # peak must exceed this to register as a performance spike
_PERF_SPIKE_RATIO = 3.0  # peak must be this many times the mean to count as a spike
_PERF_MAX_PATHS = 20  # fetch up to this many endpoints for anomaly analysis
_SLOW_QUERY_MAX_LOGS = 500  # slow log rows to fetch before normalizing
_SLOW_QUERY_TOP = 5  # normalized queries to keep in the payload
_DQL_STATEMENTS = ("select", "update", "delete", "insert")
_PROCESSLIST_MAX = 10  # longest-running connections to keep from a live processlist
_WEB_ERROR_TAIL_LINES = 500  # scan only the tail of the log to bound processing time
_WEB_ERROR_MAX_ERRORS = 10  # return at most this many recent error blocks
_WEB_ERROR_LOG_REGEX = re.compile(
	r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4})\] \[(\d+)\] \[(\w+)\] (.*)"
)


class TimeWindow:
	"""
	The stretch of time an investigation looks at, centred on the time of interest.

	Support tickets name a moment ("the site was down around 3pm"), so the window
	spans _WINDOW_HALF_HOURS either side of it rather than trailing from now.
	"""

	def __init__(self, centre: datetime | str | None = None):
		self.centre = frappe.utils.get_datetime(centre) if centre else frappe.utils.now_datetime()
		self.start = frappe.utils.add_to_date(self.centre, hours=-_WINDOW_HALF_HOURS)
		self.end = frappe.utils.add_to_date(self.centre, hours=_WINDOW_HALF_HOURS)
		self.hours = _WINDOW_HALF_HOURS * 2

	def utc_range(self) -> tuple[str, str]:
		"""ISO strings for Elasticsearch @timestamp ranges, which are always UTC."""
		return convert_user_timezone_to_utc(self.start), convert_user_timezone_to_utc(self.end)

	def covers_now(self) -> bool:
		"""Whether the investigation is about a problem that is still happening."""
		return self.start <= frappe.utils.now_datetime() <= self.end

	def epoch_range(self) -> tuple[int, int]:
		"""Unix timestamps for Prometheus range queries."""
		start, end = self.utc_range()
		return int(frappe.utils.get_datetime(start).timestamp()), int(
			frappe.utils.get_datetime(end).timestamp()
		)


def collect_site_context(site_name: str, centre: datetime | str | None = None) -> dict[str, Any]:
	window = TimeWindow(centre)
	site = _get_site(site_name)
	bench = get_bench_health(site.get("bench"))
	db_server = bench.get("database_server") if bench else None

	app_server_metrics = get_server_metrics(site.get("server"), window)
	db_server_metrics = get_server_metrics(db_server, window, is_db_server=True)

	server_advanced_analytics = (
		get_server_advanced_analytics(site.get("server"), site_name)
		if _any_spike(app_server_metrics, db_server_metrics)
		else None
	)

	return {
		"window": {"centre": window.centre, "start": window.start, "end": window.end},
		"site": get_site_health(site),
		"bench": bench,
		"apps": get_app_versions(site.get("bench")),
		"deployments": get_deployment_timeline(site_name),
		"background_jobs": get_background_job_summary(site_name, window),
		"backups": get_backup_status(site_name),
		"domains": get_domain_status(site_name),
		"incidents": get_platform_incidents(site),
		"errors": get_redacted_error_summary(site_name, window),
		"app_server_metrics": app_server_metrics,
		"db_server_metrics": db_server_metrics,
		"server_advanced_analytics": server_advanced_analytics,
		"bench_processes": get_bench_process_status(site.get("bench")),
		"site_uptime": get_site_uptime(site_name),
		"site_performance": get_site_performance_summary(site_name, site.get("bench"), window),
		"slow_queries": get_slow_queries(site_name, window),
		"database_processes": get_database_processes(site_name, window, db_server_metrics),
		"database_slow_query_share": get_database_tenant_share(
			db_server, site_name, window, db_server_metrics
		),
		"app_server_request_share": get_app_server_tenant_share(
			site.get("server"), site_name, site.get("bench"), window, app_server_metrics
		),
		"web_error_log": get_web_error_log(site.get("bench")),
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


def get_bench_process_status(bench_name: str | None) -> dict[str, Any]:
	if not bench_name:
		return {"available": False}

	try:
		processes = frappe.get_doc("Bench", bench_name).supervisorctl_status()
	except Exception:
		return {"available": False}

	_RUNNING = {"Running", "Starting"}
	stopped = [p for p in processes if p.get("status") not in _RUNNING]
	return {
		"available": True,
		"total": len(processes),
		"stopped_count": len(stopped),
		"stopped_processes": [
			{"name": p["name"], "status": p["status"], "message": p.get("message")} for p in stopped
		],
	}


def get_site_uptime(site_name: str) -> dict[str, Any]:
	"""Current ping status and HTTP response code from the blackbox exporter."""
	if not frappe.db.get_single_value("Press Settings", "monitor_server"):
		return {"available": False}

	from press.mcp.tools.telemetry.clients import prometheus_get

	try:
		success_response = prometheus_get(
			"query",
			{"query": f'probe_success{{job="site",instance="{site_name}"}}'},
		)
		status_response = prometheus_get(
			"query",
			{"query": f'probe_http_status_code{{job="site",instance="{site_name}"}}'},
		)
	except Exception:
		return {"available": False}

	up = _prom_instant(success_response)
	http_status = _prom_instant(status_response)
	return {
		"available": True,
		"up": bool(up) if up is not None else None,
		"http_status_code": int(http_status) if http_status is not None else None,
	}


def _prom_instant(response: dict) -> float | None:
	"""Return the first value from a Prometheus instant-query (vector) response."""
	result = (response.get("data") or {}).get("result") or []
	if not result:
		return None
	_, v = result[0].get("value") or (None, None)
	if v is None:
		return None
	try:
		f = float(v)
		return None if math.isnan(f) else f
	except (TypeError, ValueError):
		return None


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


def get_background_job_summary(site_name: str, window: TimeWindow) -> dict[str, Any]:
	jobs = frappe.get_all(
		"Agent Job",
		filters={"site": site_name, "creation": ("between", [window.start, window.end])},
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
		"window_hours": window.hours,
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


def get_redacted_error_summary(site_name: str, window: TimeWindow) -> dict[str, Any]:
	failed_jobs = frappe.get_all(
		"Agent Job",
		filters={
			"site": site_name,
			"status": ("in", ["Failure", "Delivery Failure"]),
			"creation": ("between", [window.start, window.end]),
		},
		fields=["job_type", "reference_doctype", "retry_count", "creation"],
		order_by="creation desc",
		limit=50,
	)

	by_job_type = Counter(job.job_type for job in failed_jobs)
	return {
		"window_hours": window.hours,
		"failed_job_count": len(failed_jobs),
		"failed_jobs_by_type": dict(by_job_type),
		"recent_failed_jobs": failed_jobs[:RECENT_LIMIT],
	}


def get_server_metrics(
	server_name: str | None, window: TimeWindow, is_db_server: bool = False
) -> dict[str, Any] | None:
	if not server_name:
		return None

	if not frappe.db.get_single_value("Press Settings", "monitor_server"):
		return {"available": False}

	from press.mcp.tools.telemetry.clients import prometheus_get

	try:
		cpu_response = prometheus_get(
			"query_range",
			_prom_params(
				f'(1 - avg(rate(node_cpu_seconds_total{{instance="{server_name}",job="node",mode="idle"}}[{_PROM_STEP}s]))) * 100',
				window,
			),
		)
	except Exception:
		return {"available": False}

	result: dict[str, Any] = {
		"available": True,
		"cpu": _summarise_series(_prom_values(cpu_response), absolute_threshold=_SPIKE_CPU_THRESHOLD),
	}

	if is_db_server:
		try:
			iops_response = prometheus_get(
				"query_range",
				_prom_params(
					f'sum(rate(node_disk_reads_completed_total{{instance="{server_name}",job="node"}}[{_PROM_STEP}s])'
					f' + rate(node_disk_writes_completed_total{{instance="{server_name}",job="node"}}[{_PROM_STEP}s]))',
					window,
				),
			)
			result["iops"] = _summarise_series(_prom_values(iops_response), ratio_threshold=_IOPS_SPIKE_RATIO)
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


def get_site_performance_summary(
	site_name: str, bench_name: str | None = None, window: TimeWindow | None = None
) -> dict[str, Any]:
	if not frappe.db.get_single_value("Press Settings", "log_server"):
		return {"available": False}

	from press.mcp.tools.telemetry.clients import elasticsearch_post

	try:
		response = elasticsearch_post(_slow_endpoint_query(site_name, window or TimeWindow()))
	except Exception:
		return {"available": False}

	custom_apps = _get_custom_app_names(bench_name)
	return {
		"available": True,
		"has_custom_apps": bool(custom_apps),
		"top_slow_endpoints": _parse_slow_endpoints(response, custom_apps),
	}


def _slow_endpoint_query(site_name: str, window: TimeWindow) -> dict:
	start, end = window.utc_range()
	return {
		"size": 0,
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.site": site_name}},
					{"match_phrase": {"json.transaction_type": "request"}},
					{"range": {"@timestamp": {"gte": start, "lte": end}}},
				]
			}
		},
		"aggs": {
			"top": {
				"terms": {
					"field": "json.request.path",
					"size": _PERF_MAX_PATHS,
					"order": {"avg_duration_ms": "desc"},
				},
				"aggs": {
					"avg_duration_ms": {"avg": {"field": "json.duration"}},
					"max_duration_ms": {"max": {"field": "json.duration"}},
				},
			}
		},
	}


def _parse_slow_endpoints(response: dict, custom_apps: set[str]) -> list[dict[str, Any]]:
	buckets = response.get("aggregations", {}).get("top", {}).get("buckets", [])
	endpoints = []
	for bucket in buckets:
		avg_ms = (bucket.get("avg_duration_ms") or {}).get("value") or 0
		peak_ms = (bucket.get("max_duration_ms") or {}).get("value") or 0
		avg_s = round(avg_ms / 1000, 3)
		peak_s = round(peak_ms / 1000, 3)
		spike_detected = (
			peak_s >= _PERF_SPIKE_PEAK_THRESHOLD_S and avg_s > 0 and peak_s >= avg_s * _PERF_SPIKE_RATIO
		)
		path = bucket.get("key") or ""
		module = _endpoint_module(path)
		endpoints.append(
			{
				"path": path,
				"avg_duration_s": avg_s,
				"peak_duration_s": peak_s,
				"spike_detected": spike_detected,
				"is_custom": module is not None and module in custom_apps,
			}
		)
	return endpoints


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


def get_slow_queries(site_name: str, window: TimeWindow) -> dict[str, Any]:
	"""
	Top MariaDB slow queries for the site's database in the investigation window, normalized.

	Normalization replaces literals with `?` so the same query with different
	values collapses into one entry. Only the normalized form is kept — the
	example query carries customer data.
	"""
	if not frappe.db.get_single_value("Press Settings", "log_server"):
		return {"available": False}

	database = frappe.db.get_value("Site", site_name, "database_name")
	if not database:
		return {"available": False}

	from press.press.report.mariadb_slow_queries.mariadb_slow_queries import (
		get_slow_query_logs,
		summarize_by_query,
	)

	start, end = window.utc_range()
	try:
		rows = get_slow_query_logs(database, start, end, None, _SLOW_QUERY_MAX_LOGS)
	except Exception:
		return {"available": False}

	rows = [row for row in rows if row["query"].lower().lstrip().startswith(_DQL_STATEMENTS)]
	summaries = summarize_by_query(rows)[:_SLOW_QUERY_TOP]

	return {
		"available": True,
		"window_hours": window.hours,
		"log_count": len(rows),
		"top_queries": [_slow_query_summary(summary) for summary in summaries],
	}


def _slow_query_summary(summary: dict) -> dict[str, Any]:
	count = int(summary["count"])
	return {
		"query": summary["query"],
		"count": count,
		"total_duration_s": round(summary["duration"], 3),
		"avg_duration_s": round(summary["duration"] / count, 3),
		"rows_examined": int(summary["rows_examined"]),
		"rows_sent": int(summary["rows_sent"]),
	}


def get_app_server_tenant_share(
	server_name: str | None,
	site_name: str,
	bench_name: str | None,
	window: TimeWindow,
	app_metrics: dict[str, Any] | None,
) -> dict[str, Any]:
	"""
	Request time on the app server split by site, collected when its CPU spiked.

	Bench containers on shared app servers have no CPU limits, so a busy neighbor
	can crowd this site out. A neighbor on the same bench is worse still — it eats
	the same gunicorn workers this site serves requests with.
	"""
	if not server_name or not (app_metrics or {}).get("cpu", {}).get("spike_detected"):
		return {"available": False}

	from press.api.analytics import AggType, ResourceType, auto_timespan_timegrain, get_request_by_

	timespan, timegrain = auto_timespan_timegrain(window.start, window.end)
	try:
		chart = get_request_by_(
			server_name,
			AggType.DURATION.value,
			get_system_timezone(),
			window.start,
			window.end,
			timespan,
			timegrain,
			ResourceType.SERVER,
		)
	except Exception:
		return {"available": False}

	share = _tenant_share(chart["datasets"], site_name, window)
	if share["available"] and not share["busiest_site_is_target"]:
		share["busiest_site_shares_bench"] = (
			frappe.db.get_value("Site", share["busiest_site"], "bench") == bench_name
		)
	return share


def get_database_tenant_share(
	db_server_name: str | None, site_name: str, window: TimeWindow, db_metrics: dict[str, Any] | None
) -> dict[str, Any]:
	"""
	Slow-query time on the database server, split between this site and its neighbors.

	The processlist can only confirm a noisy neighbor while the problem is still
	happening; for an incident that has passed, the slow log is the record of who
	was working the database. Grouping slow logs by site already exists for the
	server analytics page, so this reuses it.
	"""
	if not db_server_name or not (db_metrics or {}).get("cpu", {}).get("spike_detected"):
		return {"available": False}

	from press.api.analytics import AggType, ResourceType, auto_timespan_timegrain, get_slow_logs

	timespan, timegrain = auto_timespan_timegrain(window.start, window.end)
	try:
		chart = get_slow_logs(
			db_server_name,
			AggType.DURATION.value,
			get_system_timezone(),
			window.start,
			window.end,
			timespan,
			timegrain,
			ResourceType.SERVER,
		)
	except Exception:
		return {"available": False}

	return _tenant_share(chart["datasets"], site_name, window)


def _tenant_share(datasets: list[dict], site_name: str, window: TimeWindow) -> dict[str, Any]:
	seconds_by_site = {
		dataset["path"]: sum(value for value in dataset["values"] if value) for dataset in datasets
	}
	seconds_by_site.pop("Other", None)  # the chart's catch-all bucket is not a tenant
	total = sum(seconds_by_site.values())
	if not total:
		return {"available": False}

	busiest_site = max(seconds_by_site, key=lambda site: seconds_by_site[site])
	return {
		"available": True,
		"window_hours": window.hours,
		"target_site_share_percent": round(seconds_by_site.get(site_name, 0) / total * 100, 1),
		"busiest_site": busiest_site,
		"busiest_site_share_percent": round(seconds_by_site[busiest_site] / total * 100, 1),
		"busiest_site_is_target": busiest_site == site_name,
	}


def get_database_processes(
	site_name: str, window: TimeWindow, db_metrics: dict[str, Any] | None
) -> dict[str, Any]:
	"""
	Live SHOW PROCESSLIST, dumped only when the database CPU is busy right now.

	The processlist reflects the current moment, so it says nothing about an
	incident that has already passed. Queries are normalized and connection
	identity (user, host, database) is dropped at the collector.
	"""
	if not window.covers_now() or not (db_metrics or {}).get("cpu", {}).get("spike_detected"):
		return {"available": False}

	from press.agent import Agent

	site = frappe.get_doc("Site", site_name)
	try:
		rows = Agent(site.server).fetch_database_processes(site)
	except Exception:
		return {"available": False}

	if not rows:
		return {"available": True, "count": 0, "processes": []}

	rows.sort(key=lambda row: row.get("time") or 0, reverse=True)
	sites_by_database = _sites_by_database(row.get("db") for row in rows)
	connections = Counter(sites_by_database.get(row.get("db")) for row in rows)
	busiest_site, busiest_connections = connections.most_common(1)[0]

	return {
		"available": True,
		"count": len(rows),
		"target_site_connections": connections.get(site_name, 0),
		"busiest_site_connections": busiest_connections,
		"busiest_site_is_target": busiest_site == site_name,
		"processes": [
			_database_process(row, sites_by_database, site_name) for row in rows[:_PROCESSLIST_MAX]
		],
	}


def _sites_by_database(databases: Iterable[str]) -> dict[str, str]:
	"""Database names in MariaDB output are opaque; map them back to sites."""
	databases = {database for database in databases if database}
	if not databases:
		return {}

	sites = frappe.get_all(
		"Site",
		filters={"database_name": ("in", list(databases))},
		fields=["name", "database_name"],
	)
	return {site.database_name: site.name for site in sites}


def _database_process(row: dict, sites_by_database: dict[str, str], target_site: str) -> dict[str, Any]:
	from press.press.report.mariadb_slow_queries.mariadb_slow_queries import normalize_query

	query = (row.get("query") or "").strip()
	site = sites_by_database.get(row.get("db") or "")
	return {
		"site": site,
		"is_target_site": site == target_site,
		"command": row.get("command"),
		"seconds": row.get("time"),
		"state": (row.get("state") or "").capitalize(),
		"query": normalize_query(query) if query else "",
	}


def get_web_error_log(bench_name: str) -> dict[str, Any]:
	"""
	Recent ERROR/CRITICAL entries from the bench-level gunicorn web.error.log.

	Reads from the bench, not the site, because gunicorn's stderr is a bench-level
	file shared across all sites on the bench. Only the exception message line (last
	line of the traceback) is included. All entries pass through redact() before
	being stored.
	"""
	from press.incident_management.support_agent.redaction import redact

	try:
		raw = frappe.get_doc("Bench", bench_name).get_server_log("web.error.log")
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


def _prom_params(query: str, window: TimeWindow) -> dict:
	start, end = window.epoch_range()
	return {"query": query, "start": start, "end": end, "step": f"{_PROM_STEP}s"}


def _prom_values(response: dict) -> list[float]:
	result = (response.get("data") or {}).get("result") or []
	values = []
	for series in result:
		for _, v in series.get("values") or []:
			try:
				f = float(v)
				if not math.isnan(f):
					values.append(f)
			except (TypeError, ValueError):
				pass
	return values


def _summarise_series(
	values: list[float],
	absolute_threshold: float | None = None,
	ratio_threshold: float = _SPIKE_RATIO,
) -> dict[str, Any]:
	if not values:
		return {"available": False, "peak": None, "mean": None, "spike_detected": False}

	peak = max(values)
	mean = sum(values) / len(values)
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
