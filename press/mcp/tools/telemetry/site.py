# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
from datetime import timezone as _tz
from typing import Literal

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.guardrails.redaction import redact
from press.mcp.tools.telemetry.clients import elasticsearch_post
from press.mcp.tools.telemetry.logs import site_log_search, slow_query_search
from press.mcp.tools.telemetry.metrics import query_prometheus_recent
from press.mcp.tools.telemetry.utils import (
	clamp_days,
	clamp_hours,
	clamp_limit,
	es_error_filter,
	hits,
	promql_label_value,
	site_database_name,
	step_for_hours,
	summarize_elasticsearch_hits,
	thin_elasticsearch_hits,
)
from press.mcp.utils import system_manager_only


@press_mcp.tool()
@system_manager_only
def investigate_site(
	site: str,
	symptom: Literal["down", "slow", "errors", "jobs", "unknown"] = "unknown",
	hours: int = 6,
) -> dict:
	"""Start here for site incidents.

	Returns a compact diagnosis, evidence and exact next tools. Use drilldown
	tools only after this identifies the likely area.
	"""
	hours = clamp_hours(hours)
	ping = _ping_site(site)
	stats = _safe_tool_result(get_site_request_stats, site, hours=hours)
	status, suspected_area = _site_status(ping, stats, symptom)
	evidence = _site_evidence(ping, stats)
	top_offenders, error_trend, new_evidence, suspected_area_override = _site_investigation_details(
		site, symptom, hours
	)
	evidence.extend(new_evidence)
	suspected_area = suspected_area_override or suspected_area

	return {
		"site": site,
		"hours": hours,
		"symptom": symptom,
		"status": status,
		"suspected_area": suspected_area,
		"evidence": evidence,
		"key_metrics": {
			"ping_ok": ping.get("ok"),
			"request_count": stats.get("request_count"),
			"p95_duration_ms": stats.get("p95_duration_ms"),
			"server_error_count": stats.get("server_error_count"),
		},
		"error_trend": error_trend,
		"top_offenders": top_offenders,
		"next_actions": _site_next_actions(symptom, status, suspected_area),
	}


@press_mcp.tool()
@system_manager_only
def check_site_health(site: str, hours: int = 1) -> dict:
	"""Broad first-look health check for a site.

	Returns compact summaries for ping, uptime, request errors, slow requests
	and recent jobs. Use search_site_logs or investigate_slow_site for raw hits.

	Use as the first step when a site is reported broken or degraded.
	Drill into specifics afterwards:
		- error timing    → get_site_error_trend
		- aggregate stats → get_site_request_stats
		- slow path       → investigate_slow_site

	Key response fields:
		ping.ok            — False means site is unreachable right now
		request_errors.total — 5xx logs and exception entries
		slow_requests.sample_hits — slowest request examples
	"""
	hours = clamp_hours(hours)
	limit = 5
	site_label = promql_label_value(site)
	uptime_query = f'avg_over_time(probe_success{{job="site", instance={site_label}}}[5m])'
	uptime = query_prometheus_recent(
		uptime_query,
		minutes=hours * 60,
		step=step_for_hours(hours),
		limit=10,
	)
	request_errors = site_log_search(
		site,
		hours=hours,
		limit=limit,
		transaction_type="request",
		extra_filters=[es_error_filter()],
		sort={"@timestamp": "desc"},
	)
	slow_requests = site_log_search(
		site,
		hours=hours,
		limit=limit,
		transaction_type="request",
		sort={"json.duration": "desc"},
	)
	recent_jobs = site_log_search(
		site,
		hours=hours,
		limit=limit,
		transaction_type="job",
		sort={"@timestamp": "desc"},
	)
	return {
		"site": site,
		"hours": hours,
		"ping": _ping_site(site),
		"uptime": uptime,
		"request_errors": request_errors,
		"slow_requests": slow_requests,
		"recent_jobs": recent_jobs,
	}


@press_mcp.tool()
@system_manager_only
def check_site_ping(site: str) -> dict:
	"""HTTP ping to https://<site>/api/method/ping.

	Returns ok=True only when HTTP 200 and message="pong".
	Use when you only need liveness — cheaper than check_site_health.
	ok=False can mean: site suspended, server down, DNS failure, or 5xx.
	"""
	return _ping_site(site)


@press_mcp.tool()
@system_manager_only
def get_site_request_stats(site: str, hours: int = 1) -> dict:
	"""Aggregate request count, avg/p95 duration and 5xx error count for a site.

	Single Elasticsearch aggregation — no raw log entries returned.
	Use to confirm whether traffic and error levels are abnormal before
	pulling logs. For per-request detail use search_site_logs.

	Key response fields:
		request_count      — total requests in window
		avg_duration_ms    — mean response time
		p95_duration_ms    — 95th-percentile response time
		server_error_count — HTTP 5xx count
	"""
	hours = clamp_hours(hours)
	body = {
		"size": 0,
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.site": site}},
					{"match_phrase": {"json.transaction_type": "request"}},
					{"range": {"@timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
				]
			}
		},
		"aggs": {
			"request_count": {"value_count": {"field": "@timestamp"}},
			"avg_duration_ms": {"avg": {"field": "json.duration"}},
			"p95_duration_ms": {"percentiles": {"field": "json.duration", "percents": [95]}},
			"server_errors": {"filter": es_error_filter()},
		},
	}
	response = elasticsearch_post(body)
	aggs = response.get("aggregations", {})
	return redact(
		{
			"source": "elasticsearch",
			"site": site,
			"hours": hours,
			"request_count": aggs.get("request_count", {}).get("value"),
			"avg_duration_ms": aggs.get("avg_duration_ms", {}).get("value"),
			"p95_duration_ms": aggs.get("p95_duration_ms", {}).get("values", {}).get("95.0"),
			"server_error_count": aggs.get("server_errors", {}).get("doc_count"),
		}
	)


@press_mcp.tool()
@system_manager_only
def get_site_error_trend(site: str, hours: int = 6) -> dict:
	"""Request count, error count and avg duration in time buckets for a site.

	Use to identify WHEN errors started — gradual degradation vs sudden spike.
	Bucket interval scales with window: ≤2h → 5m, ≤12h → 15m, ≤72h → 1h, else 6h.
	Errors are HTTP 5xx responses or exception entries.

	After spotting the spike time, use search_site_logs filtered to that window
	or inspect_trace_id on a specific request to drill further.
	"""
	hours = clamp_hours(hours)
	interval = _trend_interval(hours)
	body = {
		"size": 0,
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.site": site}},
					{"match_phrase": {"json.transaction_type": "request"}},
					{"range": {"@timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
				]
			}
		},
		"aggs": {
			"over_time": {
				"date_histogram": {"field": "@timestamp", "fixed_interval": interval},
				"aggs": {
					"requests": {"value_count": {"field": "@timestamp"}},
					"errors": {"filter": es_error_filter()},
					"avg_duration_ms": {"avg": {"field": "json.duration"}},
				},
			}
		},
	}
	response = elasticsearch_post(body)
	buckets = response.get("aggregations", {}).get("over_time", {}).get("buckets", [])
	return redact(
		{
			"source": "elasticsearch",
			"site": site,
			"hours": hours,
			"bucket_interval": interval,
			"buckets": [
				{
					"time": b.get("key_as_string"),
					"requests": b.get("requests", {}).get("value", 0),
					"errors": b.get("errors", {}).get("doc_count", 0),
					"avg_duration_ms": b.get("avg_duration_ms", {}).get("value"),
				}
				for b in buckets
			],
		}
	)


@press_mcp.tool()
@system_manager_only
def get_top_slow_paths(site: str, hours: int = 6, limit: int = 10) -> dict:
	"""Top request paths by max duration for a site.

	Aggregation-only: returns buckets, not raw request hits.
	Use before pulling slow request samples.
	"""
	hours = clamp_hours(hours)
	limit = clamp_limit(limit or 10)
	body = _site_request_aggregation_body(
		site,
		hours,
		terms_field="json.request.path",
		limit=limit,
		order={"max_duration_ms": "desc"},
	)
	return _top_bucket_response(
		elasticsearch_post(body), site=site, hours=hours, limit=limit, bucket_key="path"
	)


@press_mcp.tool()
@system_manager_only
def get_top_error_paths(site: str, hours: int = 6, limit: int = 10) -> dict:
	"""Top request paths with HTTP 5xx responses or exceptions.

	Aggregation-only: returns buckets, not raw request hits.
	Use before pulling error samples.
	"""
	hours = clamp_hours(hours)
	limit = clamp_limit(limit or 10)
	body = _site_request_aggregation_body(
		site,
		hours,
		terms_field="json.request.path",
		limit=limit,
		order={"_count": "desc"},
		extra_filters=[es_error_filter()],
	)
	return _top_bucket_response(
		elasticsearch_post(body), site=site, hours=hours, limit=limit, bucket_key="path"
	)


@press_mcp.tool()
@system_manager_only
def get_status_code_breakdown(site: str, hours: int = 6) -> dict:
	"""Status-code counts for recent site requests.

	Aggregation-only: returns counts from app and HTTP response fields.
	"""
	hours = clamp_hours(hours)
	body = {
		"size": 0,
		"query": {"bool": {"filter": _site_request_filters(site, hours)}},
		"aggs": {
			"json_status_codes": {"terms": {"field": "json.response.status_code", "size": 20}},
			"http_status_codes": {"terms": {"field": "http.response.status_code", "size": 20}},
		},
	}
	response = elasticsearch_post(body)
	aggs = response.get("aggregations", {})
	return redact(
		{
			"source": "elasticsearch",
			"site": site,
			"hours": hours,
			"json_status_codes": _simple_buckets(aggs.get("json_status_codes", {}).get("buckets", [])),
			"http_status_codes": _simple_buckets(aggs.get("http_status_codes", {}).get("buckets", [])),
		}
	)


@press_mcp.tool()
@system_manager_only
def get_top_slow_jobs(site: str, hours: int = 6, limit: int = 10) -> dict:
	"""Top background jobs by max duration for a site.

	Aggregation-only: returns buckets, not raw job hits.
	Use before pulling slow job samples.
	"""
	hours = clamp_hours(hours)
	limit = clamp_limit(limit or 10)
	body = _site_request_aggregation_body(
		site,
		hours,
		transaction_type="job",
		terms_field="json.job.method",
		limit=limit,
		order={"max_duration_ms": "desc"},
	)
	return _top_bucket_response(
		elasticsearch_post(body), site=site, hours=hours, limit=limit, bucket_key="job"
	)


@press_mcp.tool()
@system_manager_only
def investigate_slow_site(site: str, hours: int = 6, limit: int = 20) -> dict:
	"""Pull the slowest requests, slowest jobs and slowest SQL queries for a site.

	Use when a site is slow but not throwing errors.
	All three result sets are sorted by duration desc.
	For error investigation use check_site_health or get_site_error_trend instead.

	Key response fields:
		slow_requests.hits[].json.request.path  — the slow endpoint
		slow_queries.hits[].mysql.slowlog.query — the slow SQL
	"""
	hours = clamp_hours(hours)
	limit = clamp_limit(limit or 20)
	database_name = site_database_name(site)
	return {
		"site": site,
		"database_name": database_name,
		"hours": hours,
		"limit_applied": limit,
		"slow_requests": site_log_search(
			site,
			hours=hours,
			limit=limit,
			transaction_type="request",
			sort={"json.duration": "desc"},
		),
		"slow_jobs": site_log_search(
			site,
			hours=hours,
			limit=limit,
			transaction_type="job",
			sort={"json.duration": "desc"},
		),
		"slow_queries": slow_query_search(database_name or site, hours=hours, limit=limit),
	}


@press_mcp.tool()
@system_manager_only
def inspect_trace_id(trace_id: str, days: int = 30, limit: int = 20) -> dict:
	"""Look up a FRAPPE_TRACE_ID in request/job logs and matching slow SQL logs.

	FRAPPE_TRACE_ID is the json.uuid field in Elasticsearch.
	Use when a user provides a trace ID or you find one in an error/exception log.

	Key response fields:
		trace_log    — the original request or job log entry (up to 1 hit)
		slow_queries — slow SQL entries tagged with this trace ID
		summary      — sites, transaction types and slowest durations seen
	"""
	if not trace_id:
		frappe.throw("trace_id is required")

	days = clamp_days(days)
	limit = clamp_limit(limit)
	time_range = {"gte": f"now-{days}d", "lte": "now"}
	trace_hits = hits(elasticsearch_post(_trace_log_query(trace_id, time_range)))
	slow_hits = hits(elasticsearch_post(_trace_slow_query(trace_id, time_range, limit or 20)))
	return redact(
		{
			"source": "elasticsearch",
			"index": "filebeat-*",
			"trace_id": trace_id,
			"days": days,
			"limit_applied": limit,
			"trace_log": thin_elasticsearch_hits(trace_hits, limit=1),
			"slow_queries": thin_elasticsearch_hits(slow_hits, limit=limit or 20),
			"summary": summarize_elasticsearch_hits(trace_hits + slow_hits),
		}
	)


@press_mcp.tool()
@system_manager_only
def get_site_performance_report(
	site: str,
	report: Literal["request_logs", "slow_queries", "deadlocks", "processlist"],
	hours: int = 24,
	limit: int = 100,
	timezone: str = "UTC",
) -> dict:
	"""Fetch a SiteInsights analytics report for a site.

	report values:
		request_logs  — top paths by count/duration for a date window (SiteInsights view)
		slow_queries  — MariaDB slow query log entries sorted by execution time
		deadlocks     — deadlock events parsed from the MariaDB error log
		processlist   — live SHOW PROCESSLIST; use for currently-stuck queries (ignores hours/limit)

	Use slow_queries or deadlocks when investigate_slow_site points to the DB layer.
	Use processlist only during an active incident — it reflects the current moment.
	"""
	hours = clamp_hours(hours)
	limit = clamp_limit(limit or 100)
	end = datetime.now(_tz.utc)
	start = end - timedelta(hours=hours)

	if report == "request_logs":
		from press.api.analytics import request_logs

		data = request_logs(site, timezone, end.strftime("%Y-%m-%d"), start=0)
		return {
			"source": "elasticsearch",
			"function": "press.api.analytics.request_logs",
			"site": site,
			"report": report,
			"data": data[:limit],
		}

	if report == "slow_queries":
		from press.api.analytics import mariadb_slow_queries

		data = mariadb_slow_queries(
			site,
			start.strftime("%Y-%m-%d %H:%M:%S"),
			end.strftime("%Y-%m-%d %H:%M:%S"),
			max_lines=limit,
		)
		return redact({"source": "elasticsearch", "site": site, "report": report, "data": data})

	if report == "deadlocks":
		from press.api.analytics import deadlock_report

		data = deadlock_report(
			site,
			start.strftime("%Y-%m-%d %H:%M:%S"),
			end.strftime("%Y-%m-%d %H:%M:%S"),
			max_log_size=limit,
		)
		return redact({"source": "elasticsearch", "site": site, "report": report, "data": data})

	if report == "processlist":
		from press.api.analytics import mariadb_processlist

		data = mariadb_processlist(site)
		return redact({"source": "agent", "site": site, "report": report, "data": data})

	frappe.throw("report must be one of request_logs, slow_queries, deadlocks, processlist")
	return None


def _site_investigation_details(
	site: str, symptom: str, hours: int
) -> tuple[dict, dict, list[str], str | None]:
	top_offenders: dict = {}
	evidence: list[str] = []
	error_trend: dict = {}
	suspected_area = None

	if symptom in {"errors", "unknown"}:
		error_trend = _add_error_aggregates(site, hours, top_offenders, evidence)
	if symptom in {"slow", "unknown"}:
		_add_slow_path_aggregates(site, hours, top_offenders, evidence)
	if symptom in {"slow", "jobs"}:
		_add_slow_job_aggregates(site, hours, top_offenders)
	if symptom == "slow":
		suspected_area = _add_slow_samples(site, hours, top_offenders, evidence)
	if symptom == "errors":
		_add_error_samples(site, hours, top_offenders, evidence)
	if symptom == "jobs":
		_add_job_samples(site, hours, top_offenders)

	return top_offenders, error_trend, evidence, suspected_area


def _add_error_aggregates(site: str, hours: int, top_offenders: dict, evidence: list[str]) -> dict:
	error_trend = _safe_tool_result(get_site_error_trend, site, hours=hours)
	error_paths = _safe_tool_result(get_top_error_paths, site, hours=hours, limit=5)
	status_codes = _safe_tool_result(get_status_code_breakdown, site, hours=hours)
	top_offenders["error_paths"] = error_paths.get("buckets", [])
	top_offenders["status_codes"] = {
		"json": status_codes.get("json_status_codes", []),
		"http": status_codes.get("http_status_codes", []),
	}
	if error_paths.get("total"):
		evidence.append("erroring paths found")
	if error_paths.get("error"):
		evidence.append("error-path lookup failed")
	return error_trend


def _add_slow_path_aggregates(site: str, hours: int, top_offenders: dict, evidence: list[str]) -> None:
	slow_paths = _safe_tool_result(get_top_slow_paths, site, hours=hours, limit=5)
	top_offenders["slow_paths"] = slow_paths.get("buckets", [])
	if slow_paths.get("error"):
		evidence.append("slow-path lookup failed")


def _add_slow_job_aggregates(site: str, hours: int, top_offenders: dict) -> None:
	slow_jobs = _safe_tool_result(get_top_slow_jobs, site, hours=hours, limit=5)
	top_offenders["slow_jobs"] = slow_jobs.get("buckets", [])


def _add_slow_samples(site: str, hours: int, top_offenders: dict, evidence: list[str]) -> str | None:
	slow = _safe_tool_result(investigate_slow_site, site, hours=hours, limit=5)
	top_offenders["slow_requests"] = slow.get("slow_requests", {}).get("sample_hits", [])
	top_offenders["slow_job_samples"] = slow.get("slow_jobs", {}).get("sample_hits", [])
	top_offenders["slow_queries"] = slow.get("slow_queries", {}).get("sample_hits", [])
	if slow.get("error"):
		evidence.append("slow-log lookup failed")
	if not slow.get("slow_queries", {}).get("returned"):
		return None

	evidence.append("slow SQL found")
	return "database"


def _add_error_samples(site: str, hours: int, top_offenders: dict, evidence: list[str]) -> None:
	errors = _safe_tool_result(
		site_log_search,
		site,
		hours=hours,
		limit=5,
		transaction_type="request",
		extra_filters=[es_error_filter()],
		sort={"@timestamp": "desc"},
	)
	top_offenders["recent_errors"] = errors.get("sample_hits", [])
	if errors.get("total"):
		evidence.append("recent 5xx responses found")
	if errors.get("error"):
		evidence.append("error-log lookup failed")


def _add_job_samples(site: str, hours: int, top_offenders: dict) -> None:
	jobs = _safe_tool_result(
		site_log_search,
		site,
		hours=hours,
		limit=5,
		transaction_type="job",
		sort={"json.duration": "desc"},
	)
	top_offenders["jobs"] = jobs.get("sample_hits", [])


def _site_request_filters(
	site: str, hours: int, transaction_type: Literal["request", "job"] = "request"
) -> list[dict]:
	return [
		{"match_phrase": {"json.site": site}},
		{"match_phrase": {"json.transaction_type": transaction_type}},
		{"range": {"@timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
	]


def _site_request_aggregation_body(
	site: str,
	hours: int,
	*,
	terms_field: str,
	limit: int,
	order: dict,
	transaction_type: Literal["request", "job"] = "request",
	extra_filters: list[dict] | None = None,
) -> dict:
	filters = _site_request_filters(site, hours, transaction_type=transaction_type)
	if extra_filters:
		filters.extend(extra_filters)

	return {
		"size": 0,
		"query": {"bool": {"filter": filters}},
		"aggs": {
			"top": {
				"terms": {"field": terms_field, "size": limit, "order": order},
				"aggs": {
					"avg_duration_ms": {"avg": {"field": "json.duration"}},
					"p95_duration_ms": {"percentiles": {"field": "json.duration", "percents": [95]}},
					"max_duration_ms": {"max": {"field": "json.duration"}},
					"errors": {"filter": es_error_filter()},
				},
			}
		},
	}


def _top_bucket_response(response: dict, *, site: str, hours: int, limit: int, bucket_key: str) -> dict:
	buckets = response.get("aggregations", {}).get("top", {}).get("buckets", [])
	return redact(
		{
			"source": "elasticsearch",
			"site": site,
			"hours": hours,
			"limit_applied": limit,
			"total": _elasticsearch_total(response),
			"buckets": [
				{
					bucket_key: bucket.get("key"),
					"count": bucket.get("doc_count", 0),
					"avg_duration_ms": bucket.get("avg_duration_ms", {}).get("value"),
					"p95_duration_ms": bucket.get("p95_duration_ms", {}).get("values", {}).get("95.0"),
					"max_duration_ms": bucket.get("max_duration_ms", {}).get("value"),
					"error_count": bucket.get("errors", {}).get("doc_count", 0),
				}
				for bucket in buckets
			],
		}
	)


def _simple_buckets(buckets: list[dict]) -> list[dict]:
	return [{"key": bucket.get("key"), "count": bucket.get("doc_count", 0)} for bucket in buckets]


def _elasticsearch_total(response: dict) -> int:
	total = response.get("hits", {}).get("total", 0)
	if isinstance(total, dict):
		return int(total.get("value") or 0)
	return int(total or 0)


def _trend_interval(hours: int) -> str:
	if hours <= 2:
		return "5m"
	if hours <= 12:
		return "15m"
	if hours <= 72:
		return "1h"
	return "6h"


def _ping_site(site: str) -> dict:
	import contextlib

	try:
		response = frappe.get_doc("Site", site).ping()
		message = None
		with contextlib.suppress(Exception):
			message = response.json().get("message")
		return {
			"source": "Site.ping",
			"url": f"https://{site}/api/method/ping",
			"status_code": response.status_code,
			"message": message,
			"ok": response.status_code == 200 and message == "pong",
			"expected": {"status_code": 200, "message": "pong"},
		}
	except Exception as e:
		return {
			"source": "Site.ping",
			"url": f"https://{site}/api/method/ping",
			"ok": False,
			"expected": {"status_code": 200, "message": "pong"},
			"error": str(e),
		}


def _site_status(ping: dict, stats: dict, symptom: str) -> tuple[str, str]:
	if not ping.get("ok"):
		return "down", "network_or_app"

	error_count = int(stats.get("server_error_count") or 0)
	p95 = float(stats.get("p95_duration_ms") or 0)
	if error_count:
		return "degraded", "app"
	if symptom == "slow" or p95 >= 2000:
		return "degraded", "app_or_database"
	return "healthy", "unknown"


def _site_evidence(ping: dict, stats: dict) -> list[str]:
	evidence = ["ping ok" if ping.get("ok") else "ping failed"]
	if stats.get("request_count") is not None:
		evidence.append(f"{int(stats.get('request_count') or 0)} requests in window")
	if stats.get("server_error_count"):
		evidence.append(f"{int(stats.get('server_error_count') or 0)} server errors")
	if stats.get("p95_duration_ms"):
		evidence.append(f"p95 request duration {int(stats['p95_duration_ms'])} ms")
	return evidence


def _site_next_actions(symptom: str, status: str, suspected_area: str) -> list[dict]:
	actions = []
	if status == "down":
		actions.append({"tool": "check_site_health", "reason": "confirm uptime and recent request failures"})
	if symptom in {"errors", "unknown"}:
		actions.append({"tool": "get_site_error_trend", "reason": "find when errors started"})
	if suspected_area in {"database", "app_or_database"}:
		actions.append(
			{"tool": "get_site_performance_report", "reason": "inspect slow queries or processlist"}
		)
	actions.append({"tool": "inspect_trace_id", "reason": "use when a sample hit has trace_id"})
	return actions


def _safe_tool_result(fn, *args, **kwargs) -> dict:
	try:
		result = fn(*args, **kwargs)
		return result if isinstance(result, dict) else {"data": result}
	except Exception as e:
		return {"error": str(e)}


def _trace_log_query(trace_id: str, time_range: dict) -> dict:
	return {
		"size": 1,
		"sort": {"@timestamp": "asc"},
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"json.uuid": trace_id}},
					{"range": {"@timestamp": time_range}},
				]
			}
		},
	}


def _trace_slow_query(trace_id: str, time_range: dict, limit: int) -> dict:
	return {
		"size": limit,
		"sort": {"@timestamp": "asc"},
		"query": {
			"bool": {
				"filter": [
					{"match_phrase": {"mysql.slowlog.query": trace_id}},
					{"range": {"@timestamp": time_range}},
				]
			}
		},
	}
