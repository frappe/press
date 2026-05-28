# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import json
from typing import Any, Literal

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.guardrails.redaction import redact
from press.mcp.tools.telemetry.clients import elasticsearch_post
from press.mcp.tools.telemetry.config import LOG_FIELDS
from press.mcp.tools.telemetry.utils import (
	clamp_hours,
	clamp_limit,
	clamp_log_chars,
	clamp_log_lines,
	hits,
	summarize_elasticsearch_hits,
	thin_elasticsearch_hits,
	trim_text,
)
from press.mcp.utils import system_manager_only

DEFAULT_SOURCE_FIELDS = [
	"@timestamp",
	"agent.name",
	"http.response.status_code",
	"json.duration",
	"json.exception",
	"json.exc",
	"json.job_name",
	"json.method",
	"json.request.method",
	"json.request.path",
	"json.response.status_code",
	"json.site",
	"json.transaction_type",
	"json.uuid",
	"message",
	"mysql.slowlog.current_user",
	"mysql.slowlog.query",
	"mysql.slowlog.schema",
	"event.duration",
]

LOG_CAPABILITIES = {
	"Elasticsearch": {
		"index": "filebeat-*",
		"fields": LOG_FIELDS,
		"fallback_tool": "query_elasticsearch",
	},
	"File logs": {
		"formatted_function": "press.api.log_browser.get_log",
		"raw_function": "press.api.log_browser.get_raw_log",
		"tool": "get_site_or_bench_log",
	},
	"Bench logs": {
		"list_function": "press.api.bench.logs",
		"log_function": "press.api.bench.log",
		"tool": "get_bench_log",
	},
}


@press_mcp.tool()
@system_manager_only
def get_log_catalog() -> dict:
	"""Get known log sources, fields and fallback tools."""
	return LOG_CAPABILITIES


@press_mcp.tool()
@system_manager_only
def query_elasticsearch(
	query: str,
	limit: int = 20,
	include_hits: bool = False,
	include_query: bool = False,
) -> dict:
	"""Run an Elasticsearch query against filebeat-*.

	Returns summary and thin hits by default. Set include_hits=True for raw hits.
	"""
	body = _parse_elasticsearch_query(query)
	body = _limit_elasticsearch_query(body, limit)
	return _run_elasticsearch(body, limit, include_hits=include_hits, include_query=include_query)


@press_mcp.tool()
@system_manager_only
def query_elasticsearch_raw(query: str, limit: int = 5, max_chars: int = 20000) -> dict:
	"""Run an Elasticsearch query and return capped raw hits.

	Use only after a summary tool identifies the exact time range, trace ID or hit.
	"""
	limit = max(1, clamp_limit(limit or 5))
	body = _parse_elasticsearch_query(query)
	body = _limit_elasticsearch_query(body, limit)
	result = _run_elasticsearch(body, limit, include_hits=True, thin_source=False)
	result["hits"] = _trim_raw_hits(result.get("hits", []), max_chars)
	return result


@press_mcp.tool()
@system_manager_only
def search_site_logs(
	site: str,
	transaction_type: Literal["request", "job"] | None = None,
	hours: int = 1,
	limit: int = 20,
	include_hits: bool = False,
	include_query: bool = False,
) -> dict:
	"""Search recent request or background job logs for a site."""
	hours = clamp_hours(hours)
	limit = clamp_limit(limit or 20)
	filters: list[dict] = [
		{"match_phrase": {"json.site": site}},
		{"range": {"@timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
	]
	if transaction_type:
		filters.append({"match_phrase": {"json.transaction_type": transaction_type}})

	body = {
		"size": limit,
		"sort": {"@timestamp": "desc"},
		"query": {"bool": {"filter": filters}},
	}
	return _run_elasticsearch(body, limit, include_hits=include_hits, include_query=include_query)


@press_mcp.tool()
@system_manager_only
def get_site_or_bench_log(
	log_type: Literal["site", "bench"],
	doc_name: str,
	log_name: str,
	formatted: bool = True,
	tail_lines: int = 200,
	max_chars: int = 20000,
) -> dict:
	"""Fetch a site or bench log through the Log Browser code path."""
	from press.api.log_browser import LOG_TYPE, get_log, get_raw_log

	log_fn = get_log if formatted else get_raw_log
	api_fn = "press.api.log_browser.get_log" if formatted else "press.api.log_browser.get_raw_log"
	return redact(
		{
			"source": "agent",
			"function": api_fn,
			"log_type": log_type,
			"doc_name": doc_name,
			"log_name": log_name,
			"log": _trim_log_payload(log_fn(LOG_TYPE(log_type), doc_name, log_name), tail_lines, max_chars),
		}
	)


@press_mcp.tool()
@system_manager_only
def get_bench_log(
	bench: str,
	log_name: str | None = None,
	tail_lines: int = 200,
	max_chars: int = 20000,
) -> dict:
	"""List bench logs or fetch one raw bench log."""
	bench_doc = frappe.get_doc("Bench", bench)
	if log_name:
		return redact(
			{
				"source": "agent",
				"function": "press.api.bench.log",
				"bench": bench,
				"log_name": log_name,
				"log": _trim_log_payload(bench_doc.get_server_log(log_name), tail_lines, max_chars),
			}
		)

	return redact(
		{
			"source": "agent",
			"function": "press.api.bench.logs",
			"bench": bench,
			"logs": bench_doc.server_logs,
		}
	)


@press_mcp.tool()
@system_manager_only
def get_bench_processes(bench: str) -> dict:
	"""Fetch supervisor processes for a bench."""
	processes = frappe.get_doc("Bench", bench).supervisorctl_status()
	return {
		"source": "agent",
		"function": "press.api.bench.get_processes",
		"bench": bench,
		"processes": processes,
	}


def site_log_search(
	site: str,
	*,
	hours: int,
	limit: int,
	transaction_type: Literal["request", "job"] | None = None,
	extra_filters: list[dict] | None = None,
	sort: dict | list | None = None,
	include_hits: bool = False,
	include_query: bool = False,
) -> dict:
	filters: list[dict] = [
		{"match_phrase": {"json.site": site}},
		{"range": {"@timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
	]
	if transaction_type:
		filters.append({"match_phrase": {"json.transaction_type": transaction_type}})
	if extra_filters:
		filters.extend(extra_filters)

	body = {
		"size": limit,
		"sort": sort or {"@timestamp": "desc"},
		"query": {"bool": {"filter": filters}},
	}
	return _run_elasticsearch(body, limit, include_hits=include_hits, include_query=include_query)


def slow_query_search(database_name: str, *, hours: int, limit: int) -> dict:
	body = {
		"size": limit,
		"sort": {"event.duration": "desc"},
		"query": {
			"bool": {
				"filter": [
					{"exists": {"field": "mysql.slowlog.query"}},
					{"range": {"@timestamp": {"gte": f"now-{hours}h", "lte": "now"}}},
				],
				"should": [
					{"match_phrase": {"mysql.slowlog.current_user": database_name}},
					{"match_phrase": {"mysql.slowlog.schema": database_name}},
				],
				"minimum_should_match": 1,
			}
		},
	}
	return _run_elasticsearch(body, limit)


def elasticsearch_response(
	response: dict,
	*,
	body: dict,
	limit: int,
	include_hits: bool = False,
	include_query: bool = False,
) -> dict:
	es_hits = hits(response)
	total = response.get("hits", {}).get("total", 0)
	if isinstance(total, dict):
		total = total.get("value", 0)

	result = {
		"source": "elasticsearch",
		"index": "filebeat-*",
		"limit_applied": clamp_limit(limit),
		"total": total,
		"returned": len(es_hits),
		"summary": summarize_elasticsearch_hits(es_hits),
		"sample_hits": thin_elasticsearch_hits(es_hits),
	}
	if include_query:
		result["body"] = redact(body)
	if include_hits:
		result["hits"] = es_hits
	if (aggs := response.get("aggregations")) is not None:
		result["aggregations"] = aggs
	return redact(result)


def _parse_elasticsearch_query(query: str | dict) -> dict:
	if isinstance(query, dict):
		return query

	try:
		body = json.loads(query)
	except json.JSONDecodeError:
		frappe.throw("Elasticsearch query must be valid JSON")

	if not isinstance(body, dict):
		frappe.throw("Elasticsearch query must be a JSON object")

	return body


def _limit_elasticsearch_query(body: dict, limit: int) -> dict:
	limit = clamp_limit(limit)
	if limit == 0:
		body["size"] = 0
		return body

	size = body.get("size")
	if size is None:
		body["size"] = limit
	elif isinstance(size, int):
		body["size"] = min(size, limit)

	return body


def _apply_default_source_fields(body: dict) -> None:
	if body.get("size", 0) and "_source" not in body:
		body["_source"] = DEFAULT_SOURCE_FIELDS


def _run_elasticsearch(
	body: dict,
	limit: int,
	*,
	include_hits: bool = False,
	thin_source: bool = True,
	include_query: bool = False,
) -> dict:
	if thin_source:
		_apply_default_source_fields(body)
	response = elasticsearch_post(body)
	return elasticsearch_response(
		response,
		body=body,
		limit=limit,
		include_hits=include_hits,
		include_query=include_query,
	)


def _trim_log_payload(log: Any, tail_lines: int, max_chars: int) -> Any:
	tail_lines = clamp_log_lines(tail_lines)
	max_chars = clamp_log_chars(max_chars)
	if isinstance(log, str):
		return trim_text(log, max_chars=max_chars, tail_lines=tail_lines)
	if isinstance(log, list):
		return {
			"items": log[-tail_lines:],
			"returned": min(len(log), tail_lines),
			"total": len(log),
			"truncated": len(log) > tail_lines,
		}
	return log


def _trim_raw_hits(es_hits: list[dict], max_chars: int) -> list[dict]:
	max_chars = clamp_log_chars(max_chars)
	return [_trim_raw_value(hit, max_chars) for hit in es_hits]


def _trim_raw_value(value: Any, max_chars: int) -> Any:
	if isinstance(value, str):
		return value if len(value) <= max_chars else value[:max_chars] + "..."
	if isinstance(value, list):
		return [_trim_raw_value(item, max_chars) for item in value]
	if isinstance(value, dict):
		return {key: _trim_raw_value(item, max_chars) for key, item in value.items()}
	return value
