# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from typing import Literal

import frappe

from press.mcp import mcp as press_mcp
from press.mcp.guardrails.redaction import redact
from press.mcp.tools.telemetry.config import EXPORTER_SCRAPE_INTERVAL
from press.mcp.tools.telemetry.metrics import query_prometheus_recent
from press.mcp.tools.telemetry.utils import promql_label_value
from press.mcp.utils import system_manager_only


@press_mcp.tool()
@system_manager_only
def check_server_health(server: str) -> dict:
	"""Prometheus health check for a server: exporters, CPU, memory, disk and containers.

	Covers app servers (Server) and proxy servers (Proxy Server).
	Each check is a 60-minute range series at 5m step.

	Key response fields:
		checks.exporter_up         — 0 means the node exporter is down
		checks.cpu_by_mode_percent — breakdown by idle/user/system/iowait
		checks.memory_used_bytes   — used = total - available
		checks.disk_used_percent   — per mountpoint
		checks.container_cpu       — per container name via cadvisor
	"""
	server_label = promql_label_value(server)
	return {
		"server": server,
		"source": "prometheus",
		"scrape_interval": EXPORTER_SCRAPE_INTERVAL,
		"checks": {
			name: query_prometheus_recent(query, minutes=60, step=300, limit=100)
			for name, query in _server_health_queries(server_label).items()
		},
	}


@press_mcp.tool()
@system_manager_only
def get_server_current_usage(server: str) -> dict:
	"""Real-time CPU and memory utilization for a server as [0, 1] fractions.

	Faster than check_server_health when you only need "is this server
	overloaded right now?" — single instant Prometheus query, no time series.
	0.0 = idle, 1.0 = fully utilized.
	"""
	from press.api.server import get_cpu_and_memory_usage

	usage = get_cpu_and_memory_usage(server)
	return {
		"source": "prometheus",
		"server": server,
		"cpu_fraction": usage.get("vcpu"),
		"memory_fraction": usage.get("memory"),
	}


@press_mcp.tool()
@system_manager_only
def get_server_storage_breakdown(server: str, server_type: Literal["Server", "Database Server"]) -> dict:
	"""Realtime storage breakdown for a server by path or database.

	server_type must match the doctype: "Server" for app servers,
	"Database Server" for DB servers.
	For disk usage trends over time use query_server_metric(metric="space") instead.
	"""
	if server_type not in ("Server", "Database Server"):
		frappe.throw("server_type must be Server or Database Server")

	data = frappe.get_doc(server_type, server).get_storage_usage()
	return redact(
		{
			"source": "agent" if server_type == "Server" else "ansible",
			"function": f"{server_type}.get_storage_usage",
			"server": server,
			"server_type": server_type,
			"data": data,
		}
	)


def _server_health_queries(server_label: str) -> dict[str, str]:
	l = server_label  # noqa: E741 — short alias keeps multi-line PromQL readable
	return {
		"exporter_up": f"up{{instance={l}}}",
		"cpu_by_mode_percent": (
			f'sum by (mode) (rate(node_cpu_seconds_total{{instance={l}, job="node"}}[5m])) * 100'
		),
		"memory_used_bytes": (
			f'node_memory_MemTotal_bytes{{instance={l}, job="node"}}'
			f' - node_memory_MemAvailable_bytes{{instance={l}, job="node"}}'
		),
		"disk_used_percent": (
			f'100 - ((node_filesystem_avail_bytes{{instance={l}, job="node", mountpoint=~"/|/var/lib/docker"}} * 100)'
			f' / node_filesystem_size_bytes{{instance={l}, job="node", mountpoint=~"/|/var/lib/docker"}})'
		),
		"container_cpu": (
			f'sum by (name) (rate(container_cpu_usage_seconds_total{{instance={l}, job="cadvisor"}}[5m]))'
		),
	}
