# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import time
from typing import Any, Literal

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.tools.telemetry.clients import prometheus_get
from press.mcp.tools.telemetry.config import (
	EXPORTER_SCRAPE_INTERVAL,
	RELEASE_GROUP_METRICS,
	SERVER_METRICS,
	SERVER_TYPE_MAP,
)
from press.mcp.tools.telemetry.utils import (
	clamp_hours,
	clamp_limit,
	clamp_relative_minutes,
	promql_regex_fragment,
	promql_string_fragment,
	server_mountpoint,
	summarize_prometheus_response,
	validate_prometheus_range,
)
from press.mcp.utils import system_manager_only


@press_mcp.tool()
@system_manager_only
def get_metric_catalog(
	topic: Literal["Server", "Release group", "Monitoring jobs"] = "Server",
) -> dict:
	"""List known dashboard metrics. Use get_metric_definition for PromQL."""
	if topic == "Server":
		return {
			"source": "press.api.server.analytics",
			"metrics": [_metric_summary(key, value) for key, value in SERVER_METRICS.items()],
		}
	if topic == "Release group":
		return {
			"source": "press.api.analytics.get_*_usage",
			"collector": "cadvisor",
			"metrics": [_metric_summary(key, value) for key, value in RELEASE_GROUP_METRICS.items()],
		}
	return get_monitoring_job_catalog()


@press_mcp.tool()
@system_manager_only
def get_metric_definition(
	topic: Literal["Server", "Release group"],
	metric: str,
) -> dict:
	"""Get one metric definition with the PromQL fallback query."""
	catalog = SERVER_METRICS if topic == "Server" else RELEASE_GROUP_METRICS
	if metric not in catalog:
		frappe.throw(f"Unknown {topic} metric. Call get_metric_catalog first.")
	return _metric_definition(metric, catalog[metric])


@press_mcp.tool()
@system_manager_only
def get_monitoring_job_catalog() -> dict:
	"""Get server type to Prometheus job mapping from monitoring.get_job_map."""
	from press.api.monitoring import get_job_map

	job_map = get_job_map()
	app_jobs = _job_regex(job_map, "app")
	proxy_jobs = _job_regex(job_map, "proxy")
	database_jobs = _job_regex(job_map, "database")
	return {
		"source_function": "press.api.monitoring.get_job_map",
		"job_map": job_map,
		"server_type_map": SERVER_TYPE_MAP,
		"file_sd_labels": {
			"instance": "server name, sometimes server:8443",
			"job": "node/nginx/docker/cadvisor/gunicorn/rq/mariadb/etc",
			"__metrics_path__": "/metrics/<job>",
			"proxy_host": "set for proxied private targets",
			"base_path": "set for proxied private targets",
		},
		"examples": [
			'up{instance="server-1", job="node"}',
			f'up{{instance="server-1", job=~"{app_jobs}"}}',
			f'up{{instance="proxy-1", job=~"{proxy_jobs}"}}',
			f'up{{instance="database-1", job=~"{database_jobs}"}}',
		],
	}


@press_mcp.tool()
@system_manager_only
def query_prometheus(
	query: str,
	unix_timestamp: int,
	limit: int = 20,
	include_series: bool = False,
	include_query: bool = False,
) -> dict:
	"""Run an instant PromQL query. Returns summary by default."""
	params: dict[str, str | int] = {"query": query, "time": unix_timestamp}
	response = prometheus_get("query", params)
	response = _limit_prometheus_response(response, limit)
	return _prometheus_response(
		response,
		query=query,
		limit=limit,
		params=params,
		include_series=include_series,
		include_query=include_query,
	)


@press_mcp.tool()
@system_manager_only
def query_prometheus_range(
	query: str,
	start_unix: int,
	end_unix: int,
	step: float,
	limit: int = 20,
	include_series: bool = False,
	include_query: bool = False,
) -> dict:
	"""Run a bounded PromQL range query. Returns min/max/avg/latest by default."""
	validate_prometheus_range(start_unix, end_unix, step)
	params: dict[str, str | int | float] = {
		"query": query,
		"start": start_unix,
		"end": end_unix,
		"step": step,
	}
	response = prometheus_get("query_range", params)
	response = _limit_prometheus_response(response, limit)
	return _prometheus_response(
		response,
		query=query,
		limit=limit,
		params={"start": start_unix, "end": end_unix, "step": step},
		include_series=include_series,
		include_query=include_query,
	)


@press_mcp.tool()
@system_manager_only
def query_prometheus_recent(
	query: str,
	minutes: int = 60,
	step: float = 300,
	limit: int = 20,
	include_series: bool = False,
	include_query: bool = False,
) -> dict:
	"""Run a PromQL range query for the last N minutes."""
	minutes = clamp_relative_minutes(minutes)
	end_unix = int(time.time())
	start_unix = end_unix - (minutes * 60)
	return query_prometheus_range(
		query,
		start_unix,
		end_unix,
		step,
		limit,
		include_series=include_series,
		include_query=include_query,
	)


@press_mcp.tool()
@system_manager_only
def query_server_metric(
	server: str,
	metric: Literal[
		"cpu",
		"loadavg",
		"memory",
		"network",
		"iops",
		"space",
		"database_uptime",
		"database_commands_count",
		"database_connections",
		"innodb_bp_size",
		"innodb_bp_size_of_total_ram",
		"innodb_bp_miss_percent",
		"innodb_avg_row_lock_time",
	],
	hours: int = 1,
	step: float = 300,
	mountpoint: str | None = None,
	limit: int = 100,
	include_series: bool = False,
	include_query: bool = False,
) -> dict:
	"""Run one known ServerCharts.vue Prometheus metric."""
	hours = clamp_hours(hours)
	query = _server_metric_query(server, metric, f"{int(step)}s", mountpoint)
	result = query_prometheus_recent(
		query,
		minutes=hours * 60,
		step=step,
		limit=limit,
		include_series=include_series,
		include_query=include_query,
	)
	result["dashboard_function"] = SERVER_METRICS[metric]["function"]
	result["metric"] = metric
	return result


@press_mcp.tool()
@system_manager_only
def query_release_group_metric(
	release_group: str,
	metric: Literal["cpu", "memory", "fs_reads", "fs_writes", "network_in", "network_out"],
	hours: int = 24,
	step: float = 300,
	limit: int = 100,
	include_series: bool = False,
	include_query: bool = False,
) -> dict:
	"""Run one known release-group cadvisor metric."""
	benches = frappe.get_all("Bench", {"status": "Active", "group": release_group}, pluck="name")
	if not benches:
		frappe.throw("No active benches found for release group")

	query = RELEASE_GROUP_METRICS[metric]["query"].replace(
		"$benches", "|".join(promql_regex_fragment(bench) for bench in benches)
	)
	result = query_prometheus_recent(
		query,
		minutes=clamp_hours(hours) * 60,
		step=step,
		limit=limit,
		include_series=include_series,
		include_query=include_query,
	)
	result["dashboard_function"] = RELEASE_GROUP_METRICS[metric]["function"]
	result["metric"] = metric
	result["release_group"] = release_group
	result["benches"] = benches
	return result


def _metric_definition(key: str, value: dict[str, str]) -> dict:
	return {
		**_metric_summary(key, value),
		"query": value["query"],
	}


def _metric_summary(key: str, value: dict[str, str]) -> dict:
	return {
		"key": key,
		"name": value["name"],
		"dashboard_function": value["function"],
		"source": value.get("source", "prometheus"),
		"job": value.get("job", "cadvisor"),
		"group_by": value.get("group_by", "name"),
	}


def _job_regex(job_map: dict[str, list[str]], server_type: str) -> str:
	return "|".join(job_map.get(server_type, []))


def _server_metric_query(server: str, metric: str, step: str, mountpoint: str | None = None) -> str:
	template = SERVER_METRICS[metric]["query"]
	mountpoint = mountpoint or server_mountpoint(server)
	return (
		template.replace("$server", promql_string_fragment(server))
		.replace("$step", step)
		.replace("$mountpoint", promql_string_fragment(mountpoint))
	)


def _prometheus_response(
	response: dict,
	*,
	query: str,
	limit: int,
	params: dict[str, Any],
	include_series: bool,
	include_query: bool,
) -> dict:
	result = {
		"source": "prometheus",
		"scrape_interval": EXPORTER_SCRAPE_INTERVAL,
		"limit_applied": clamp_limit(limit),
		"status": response.get("status"),
		"summary": summarize_prometheus_response(response),
	}
	if include_query:
		result["query"] = query
		result["params"] = params
	if include_series:
		result["data"] = response.get("data")
	return result


def _limit_prometheus_response(response: dict, limit: int) -> dict:
	limit = clamp_limit(limit)
	if not limit:
		return response

	result = response.get("data", {}).get("result")
	if isinstance(result, list):
		response["data"]["result"] = result[:limit]

	return response
