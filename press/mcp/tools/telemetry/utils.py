# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import json
from typing import Any

import frappe

from press.mcp.tools.telemetry.config import (
	MAX_LIMIT,
	MAX_LOG_CHARS,
	MAX_LOG_LINES,
	MAX_RANGE_SECONDS,
	MAX_RELATIVE_MINUTES,
	MIN_STEP_SECONDS,
)
from press.mcp.utils import _clamp

PROMETHEUS_LABELS = {
	"command",
	"device",
	"instance",
	"job",
	"mode",
	"mountpoint",
	"name",
}


def clamp_limit(limit: int | None) -> int:
	return _clamp(limit, 0, 0, MAX_LIMIT)


def clamp_hours(hours: int | None) -> int:
	return _clamp(hours, 1, 1, 24 * 30)


def clamp_days(days: int | None) -> int:
	return _clamp(days, 30, 1, 90)


def clamp_log_chars(max_chars: int | None) -> int:
	return _clamp(max_chars, MAX_LOG_CHARS, 1000, MAX_LOG_CHARS)


def clamp_log_lines(lines: int | None) -> int:
	return _clamp(lines, 200, 1, MAX_LOG_LINES)


def clamp_relative_minutes(minutes: int | None) -> int:
	return _clamp(minutes, 60, 1, MAX_RELATIVE_MINUTES)


def validate_prometheus_range(start_unix: int, end_unix: int, step: float) -> None:
	try:
		start_unix = int(start_unix)
		end_unix = int(end_unix)
		step = float(step)
	except (TypeError, ValueError):
		frappe.throw(
			"start_unix, end_unix and step must be numeric. Please provide valid Unix timestamps and step in seconds."
		)

	if start_unix > end_unix:
		frappe.throw(
			"start_unix must be before end_unix. Please check that start_unix is a smaller timestamp."
		)
	if end_unix - start_unix > MAX_RANGE_SECONDS:
		frappe.throw("Range query cannot exceed 30 days. Please reduce the time range.")
	if step < MIN_STEP_SECONDS:
		frappe.throw("step must be at least 60 seconds. Use a value of 60 or higher.")


def step_for_hours(hours: int) -> int:
	if hours <= 6:
		return 300
	if hours <= 24:
		return 900
	return 3600


def as_float(value: Any) -> float | None:
	try:
		return float(value)
	except (TypeError, ValueError):
		return None


def hits(response: dict) -> list[dict]:
	return response.get("hits", {}).get("hits", [])


def thin_elasticsearch_hit(hit: dict) -> dict:
	source = hit.get("_source", {})
	json_data = source.get("json", {})
	request = json_data.get("request") or {}
	response = json_data.get("response") or {}
	http_response = source.get("http", {}).get("response") or {}
	mysql = source.get("mysql", {}).get("slowlog") or {}

	return {
		"id": hit.get("_id"),
		"timestamp": source.get("@timestamp"),
		"site": json_data.get("site"),
		"transaction_type": json_data.get("transaction_type"),
		"duration_ms": json_data.get("duration"),
		"event_duration_ms": _event_duration_ms(source),
		"status_code": response.get("status_code") or http_response.get("status_code"),
		"method": request.get("method"),
		"path": request.get("path"),
		"job": json_data.get("job_name") or json_data.get("method"),
		"trace_id": json_data.get("uuid"),
		"exception": bool(json_data.get("exception") or json_data.get("exc")),
		"sql_user": mysql.get("current_user"),
		"sql_schema": mysql.get("schema"),
		"sql_query": _shorten(mysql.get("query"), 500),
		"message": _shorten(source.get("message"), 500),
	}


def thin_elasticsearch_hits(es_hits: list[dict], limit: int = 3) -> list[dict]:
	return [thin_elasticsearch_hit(hit) for hit in es_hits[:limit]]


def summarize_elasticsearch_hits(es_hits: list[dict]) -> dict:
	sites: set[str] = set()
	transaction_types: set[str] = set()
	agents: set[str] = set()
	slowest_duration_ms = None
	slowest_event_duration_ms = None

	for hit in es_hits:
		source = hit.get("_source", {})
		json_data = source.get("json", {})
		if json_data.get("site"):
			sites.add(json_data["site"])
		if json_data.get("transaction_type"):
			transaction_types.add(json_data["transaction_type"])
		if source.get("agent", {}).get("name"):
			agents.add(source["agent"]["name"])

		duration = as_float(json_data.get("duration"))
		if duration is not None:
			slowest_duration_ms = max(slowest_duration_ms or 0, duration)

		event_duration = as_float(source.get("event", {}).get("duration"))
		if event_duration is not None:
			slowest_event_duration_ms = max(slowest_event_duration_ms or 0, event_duration / 1e6)

	return {
		"slowest_duration_ms": slowest_duration_ms,
		"slowest_event_duration_ms": slowest_event_duration_ms,
		"sites_seen": sorted(sites),
		"transaction_types": sorted(transaction_types),
		"agents_seen": sorted(agents),
	}


def summarize_prometheus_data(data: dict, summary_limit: int = 20) -> dict:
	result = data.get("result")
	if not isinstance(result, list):
		return {"result_type": data.get("resultType"), "series": 0}

	series = []
	for item in result:
		values = item.get("values") or []
		if values:
			numbers = []
			for _, raw in values:
				value = as_float(raw)
				if value is not None:
					numbers.append(value)
			latest = numbers[-1] if numbers else None
		else:
			raw_value = item.get("value") or []
			latest = as_float(raw_value[1]) if len(raw_value) > 1 else None
			numbers = [latest] if latest is not None else []

		series.append(
			{
				"metric": _prometheus_labels(item.get("metric", {})),
				"points": len(values) or int(bool(numbers)),
				"latest": latest,
				"min": min(numbers) if numbers else None,
				"max": max(numbers) if numbers else None,
				"avg": sum(numbers) / len(numbers) if numbers else None,
			}
		)

	return {
		"result_type": data.get("resultType"),
		"series": len(result),
		"series_summary": series[:summary_limit],
		"series_summary_truncated": len(series) > summary_limit,
		"top_series_by_max": sorted(series, key=_prometheus_series_max, reverse=True)[:5],
	}


def summarize_prometheus_response(response: dict, summary_limit: int = 20) -> dict:
	return summarize_prometheus_data(response.get("data") or {}, summary_limit=summary_limit)


def es_error_filter() -> dict:
	return {
		"bool": {
			"should": [
				{"range": {"json.response.status_code": {"gte": 500}}},
				{"range": {"http.response.status_code": {"gte": 500}}},
				{"exists": {"field": "json.exception"}},
				{"exists": {"field": "json.exc"}},
			],
			"minimum_should_match": 1,
		}
	}


def trim_text(value: str, *, max_chars: int, tail_lines: int | None = None) -> dict:
	all_lines = value.splitlines()
	lines = all_lines
	if tail_lines is not None:
		lines = lines[-tail_lines:]

	text = "\n".join(lines)
	truncated_chars = max(0, len(text) - max_chars)
	if truncated_chars:
		text = text[-max_chars:]

	return {
		"text": text,
		"lines_returned": len(lines),
		"chars_returned": len(text),
		"truncated": truncated_chars > 0 or (tail_lines is not None and len(all_lines) > tail_lines),
	}


def promql_label_value(value: str) -> str:
	return json.dumps(value)


def promql_string_fragment(value: str) -> str:
	return json.dumps(value)[1:-1]


def promql_regex_fragment(value: str) -> str:
	return promql_string_fragment(value).replace("|", "\\|")


def site_database_name(site: str) -> str | None:
	try:
		return frappe.db.get_value("Site", site, "database_name")
	except Exception:
		return None


def server_mountpoint(server: str) -> str:
	try:
		from press.api.server import get_mount_point

		return get_mount_point(server)
	except Exception:
		return "/|/var/lib/docker"


def _event_duration_ms(source: dict) -> float | None:
	duration = as_float(source.get("event", {}).get("duration"))
	if duration is None:
		return None
	return duration / 1e6


def _prometheus_labels(labels: dict) -> dict:
	return {key: value for key, value in labels.items() if key in PROMETHEUS_LABELS}


def _prometheus_series_max(series: dict) -> float:
	return as_float(series.get("max")) or 0


def _shorten(value: Any, max_chars: int) -> Any:
	if not isinstance(value, str) or len(value) <= max_chars:
		return value
	return value[:max_chars] + "..."
