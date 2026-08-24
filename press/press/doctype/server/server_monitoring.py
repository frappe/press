# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from contextlib import suppress
from typing import TypedDict

import frappe
import requests
from frappe.utils.password import get_decrypted_password

from press.utils import log_error
from press.utils.raven import send_raven_message

RAVEN_SERVER_ALERTS_CHANNEL = "frappe-cloud-server-alerts"
PROMETHEUS_REGEX_META_CHAR_PATTERN = re.compile(r"([\\.^$*+?()[\]{}|])")
# Hetzner volumes do not grow on demand, so disk decides where new sites go
DISK_AWARE_PROVIDERS = ["Hetzner"]
MINIMUM_SITE_DISK_BYTES = 50 * 1024 * 1024 * 1024
MINIMUM_SITE_DISK_RATIO = 0.5


class PublicServerHealthMetrics(TypedDict):
	available_memory_bytes: dict[str, float]
	available_memory_ratio: dict[str, float]
	cpu_idle_ratio: dict[str, float]
	oom_kills: dict[str, float]
	available_disk_bytes: dict[str, float]
	available_disk_ratio: dict[str, float]


class PublicServerPoolDecision(TypedDict):
	selected_bench_servers: set[str]
	selected_site_servers: set[str]
	servers_with_decision: set[str]
	server_issues: dict[str, list[str]]
	fallback_servers_by_cluster: dict[str, str]


def monitor_server_and_refresh_new_bench_and_site_server_pool() -> None:
	"""Refresh `use_for_new_benches` and `use_for_new_sites` flags for public clusters
	1. Consider active, public primary servers for each cluster
	2. Fetch memory, CPU and OOM-kill health for all servers in bulk from Prometheus
	3. Prefer healthy servers, and fall back to the least-bad server when a cluster has no healthy candidates
	4. Keep new sites away from Hetzner servers that are low on disk, and alert about them
	"""
	server_names, servers_by_cluster, disk_aware_servers = _get_public_primary_servers_by_cluster()
	if not server_names:
		return

	metrics = _get_public_server_health_metrics(server_names, disk_aware_servers)
	if not metrics:
		return

	pool_decision = _get_public_server_pool_decision(servers_by_cluster, metrics)
	_apply_public_server_pool_decision(server_names, pool_decision)
	_send_public_server_pool_health_alert(pool_decision["server_issues"])
	_send_low_disk_alert(pool_decision["selected_site_servers"], metrics)
	_create_no_suitable_servers_incident(pool_decision["fallback_servers_by_cluster"], metrics)


def _get_public_primary_servers_by_cluster() -> tuple[list[str], dict[str, list[str]], list[str]]:
	servers = frappe.get_all(
		"Server",
		filters={"status": "Active", "is_primary": True, "public": True, "exclude_for_scheduling": False},
		fields=["name", "cluster", "provider"],
	)
	server_names = [server.name for server in servers]
	servers_by_cluster: dict[str, list[str]] = {}
	for server in servers:
		servers_by_cluster.setdefault(server.cluster, []).append(server.name)
	disk_aware_servers = [server.name for server in servers if server.provider in DISK_AWARE_PROVIDERS]
	return server_names, servers_by_cluster, disk_aware_servers


def _get_public_server_pool_decision(
	servers_by_cluster: dict[str, list[str]],
	metrics: PublicServerHealthMetrics,
) -> PublicServerPoolDecision:
	ram_available_ratio = metrics["available_memory_ratio"]
	cpu_idle_ratio = metrics["cpu_idle_ratio"]

	decision: PublicServerPoolDecision = {
		"selected_bench_servers": set(),
		"selected_site_servers": set(),
		"servers_with_decision": set(),
		"server_issues": {},
		"fallback_servers_by_cluster": {},
	}

	for cluster, cluster_servers in servers_by_cluster.items():
		candidates = [
			server for server in cluster_servers if server in ram_available_ratio and server in cpu_idle_ratio
		]
		if not candidates:
			continue

		for server in candidates:
			issues = _get_public_server_health_issues(server, metrics)
			if issues:
				decision["server_issues"][server] = issues

		healthy_servers = [
			server
			for server in candidates
			if ram_available_ratio[server] >= 0.2 and cpu_idle_ratio[server] >= 0.5
		]
		decision["servers_with_decision"].update(cluster_servers)

		if healthy_servers:
			decision["selected_bench_servers"].add(
				max(sorted(healthy_servers), key=lambda server: _get_bench_pool_score(server, metrics))
			)
			site_servers = _servers_with_enough_disk(healthy_servers, metrics["available_disk_bytes"])
			decision["selected_site_servers"].add(
				max(sorted(site_servers), key=lambda server: _get_site_pool_score(server, metrics))
			)
			continue

		selected_server = max(
			sorted(candidates), key=lambda server: _get_least_bad_pool_score(server, metrics)
		)
		decision["selected_bench_servers"].add(selected_server)
		decision["selected_site_servers"].add(selected_server)
		decision["fallback_servers_by_cluster"][cluster] = selected_server

	for server, oom_kills in metrics["oom_kills"].items():
		if oom_kills > 4:
			decision["server_issues"].setdefault(server, []).append(
				f"OOM kills in the last 60 minutes: {max(1, round(oom_kills))}"
			)

	return decision


def _servers_with_enough_disk(server_names: list[str], available_disk_bytes: dict[str, float]) -> list[str]:
	"""Drop servers that are low on disk. Only disk-aware providers are in the map."""
	servers = [
		server
		for server in server_names
		if available_disk_bytes.get(server, MINIMUM_SITE_DISK_BYTES) >= MINIMUM_SITE_DISK_BYTES
	]
	return servers or server_names


def _get_public_server_health_issues(server: str, metrics: PublicServerHealthMetrics) -> list[str]:
	issues = []
	ram_utilization = 1 - metrics["available_memory_ratio"][server]
	cpu_utilization = 1 - metrics["cpu_idle_ratio"][server]

	if ram_utilization > 0.8:
		issues.append(f"RAM utilization: {ram_utilization * 100:.2f}%")
	if cpu_utilization > 0.5:
		issues.append(f"CPU utilization: {cpu_utilization * 100:.2f}%")

	return issues


def _get_bench_pool_score(
	server: str, metrics: PublicServerHealthMetrics
) -> tuple[float, float, float, float]:
	ram_available_ratio = metrics["available_memory_ratio"].get(server, 0.0)
	cpu_idle_ratio = metrics["cpu_idle_ratio"].get(server, 0.0)
	return (
		min(ram_available_ratio, cpu_idle_ratio),
		ram_available_ratio,
		cpu_idle_ratio,
		metrics["available_memory_bytes"].get(server, 0.0),
	)


def _get_site_pool_score(
	server: str, metrics: PublicServerHealthMetrics
) -> tuple[float, float, float, float]:
	ram_available_ratio = metrics["available_memory_ratio"].get(server, 0.0)
	cpu_idle_ratio = metrics["cpu_idle_ratio"].get(server, 0.0)
	return (
		min(cpu_idle_ratio, ram_available_ratio),
		cpu_idle_ratio,
		ram_available_ratio,
		metrics["available_memory_bytes"].get(server, 0.0),
	)


def _get_least_bad_pool_score(
	server: str, metrics: PublicServerHealthMetrics
) -> tuple[int, float, float, float]:
	failed_check_count = len(_get_public_server_health_issues(server, metrics))
	return (
		-failed_check_count,
		metrics["cpu_idle_ratio"].get(server, 0.0),
		metrics["available_memory_ratio"].get(server, 0.0),
		metrics["available_memory_bytes"].get(server, 0.0),
	)


def _apply_public_server_pool_decision(
	server_names: list[str],
	decision: PublicServerPoolDecision,
) -> None:
	servers_with_decision = decision["servers_with_decision"]
	if not servers_with_decision:
		return

	bench_servers_to_disable = list(servers_with_decision - decision["selected_bench_servers"])
	site_servers_to_disable = list(servers_with_decision - decision["selected_site_servers"])
	if bench_servers_to_disable:
		frappe.db.set_value(
			"Server",
			{"name": ["in", bench_servers_to_disable]},
			{"use_for_new_benches": 0},
			update_modified=False,
		)
	if site_servers_to_disable:
		frappe.db.set_value(
			"Server",
			{"name": ["in", site_servers_to_disable]},
			{"use_for_new_sites": 0},
			update_modified=False,
		)

	selected_bench_servers = list(decision["selected_bench_servers"] & set(server_names))
	selected_site_servers = list(decision["selected_site_servers"] & set(server_names))
	if selected_bench_servers:
		frappe.db.set_value(
			"Server",
			{"name": ["in", selected_bench_servers]},
			{"use_for_new_benches": 1},
			update_modified=False,
		)
	if selected_site_servers:
		frappe.db.set_value(
			"Server",
			{"name": ["in", selected_site_servers]},
			{"use_for_new_sites": 1},
			update_modified=False,
		)


def _get_public_server_health_metrics(
	server_names: list[str],
	disk_aware_servers: list[str] | None = None,
) -> PublicServerHealthMetrics | None:
	"""Fetch memory, CPU, kernel OOM-kill and disk metrics for public servers from Prometheus."""
	if not server_names:
		return None

	prometheus_connection = _get_public_server_pool_prometheus_connection()
	if not prometheus_connection:
		return None
	url, auth = prometheus_connection

	instance_matcher = "|".join(_escape_prometheus_regex_literal(name) for name in server_names)

	available_memory_bytes_query = f'avg_over_time(node_memory_MemAvailable_bytes{{instance=~"^({instance_matcher})$", job="node"}}[60m])'
	available_memory_ratio_query = (
		f'avg_over_time(node_memory_MemAvailable_bytes{{instance=~"^({instance_matcher})$", job="node"}}[60m])'
		f' / avg_over_time(node_memory_MemTotal_bytes{{instance=~"^({instance_matcher})$", job="node"}}[60m])'
	)
	cpu_idle_ratio_query = (
		f'avg by (instance) (rate(node_cpu_seconds_total{{instance=~"^({instance_matcher})$", '
		f'job="node", mode="idle"}}[60m]))'
	)
	oom_kills_query = (
		f'sum by (instance) (increase(node_vmstat_oom_kill{{instance=~"^({instance_matcher})$", '
		f'job="node"}}[60m])) > 4'
	)

	available_memory_bytes_results = _query_prometheus_vector(available_memory_bytes_query, url, auth)
	available_memory_ratio_results = _query_prometheus_vector(available_memory_ratio_query, url, auth)
	cpu_idle_ratio_results = _query_prometheus_vector(cpu_idle_ratio_query, url, auth)
	oom_kills_results = _query_prometheus_vector(oom_kills_query, url, auth)

	if (
		available_memory_bytes_results is None
		or available_memory_ratio_results is None
		or cpu_idle_ratio_results is None
	):
		return None

	available_disk_bytes, available_disk_ratio = _get_available_disk(disk_aware_servers or [], url, auth)

	return {
		"available_memory_bytes": _build_public_server_metric_map(
			server_names, available_memory_bytes_results
		),
		"available_memory_ratio": _build_public_server_metric_map(
			server_names, available_memory_ratio_results
		),
		"cpu_idle_ratio": _build_public_server_metric_map(server_names, cpu_idle_ratio_results),
		"oom_kills": _build_public_server_metric_map(server_names, oom_kills_results, default=0.0),
		"available_disk_bytes": available_disk_bytes,
		"available_disk_ratio": available_disk_ratio,
	}


def _get_available_disk(
	server_names: list[str],
	url: str,
	auth: tuple[str, str],
) -> tuple[dict[str, float], dict[str, float]]:
	"""Fetch free bytes and free ratio of the fullest volume that holds benches."""
	from press.press.doctype.server.server import BENCH_DATA_MNT_POINT  # circular import

	if not server_names:
		return {}, {}

	instance_matcher = "|".join(_escape_prometheus_regex_literal(name) for name in server_names)
	labels = f'instance=~"^({instance_matcher})$", job="node", mountpoint=~"/|{BENCH_DATA_MNT_POINT}"'
	available_disk_bytes_query = f"min by (instance) (node_filesystem_avail_bytes{{{labels}}})"
	available_disk_ratio_query = (
		f"min by (instance) (node_filesystem_avail_bytes{{{labels}}}"
		f" / node_filesystem_size_bytes{{{labels}}})"
	)

	return (
		_build_public_server_metric_map(
			server_names, _query_prometheus_vector(available_disk_bytes_query, url, auth)
		),
		_build_public_server_metric_map(
			server_names, _query_prometheus_vector(available_disk_ratio_query, url, auth)
		),
	)


def _get_public_server_pool_prometheus_connection() -> tuple[str, tuple[str, str]] | None:
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	if not monitor_server:
		return None

	url = f"https://{monitor_server}/prometheus/api/v1/query"
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")
	return url, ("frappe", str(password))


def _escape_prometheus_regex_literal(value: str) -> str:
	"""Escape a literal for a Prometheus RE2 regex label matcher."""
	return PROMETHEUS_REGEX_META_CHAR_PATTERN.sub(r"\\\\\1", value)


def _build_public_server_metric_map(
	server_names: list[str],
	results: list[dict] | None,
	default: float | None = None,
) -> dict[str, float]:
	server_map: dict[str, float] = {}
	if default is not None:
		server_map = {name: default for name in server_names}
	if results is None:
		return server_map

	server_name_set = set(server_names)
	for result in results:
		instance = result.get("metric", {}).get("instance")
		if not instance or instance not in server_name_set:
			continue
		with suppress(KeyError, TypeError, ValueError):
			server_map[instance] = float(result["value"][1])
	return server_map


def _query_prometheus_vector(query: str, url: str, auth: tuple[str, str]) -> list[dict] | None:
	try:
		response = requests.get(url, params={"query": query}, auth=auth, timeout=30)
		data = response.json()
	except (ValueError, requests.exceptions.RequestException) as exc:
		log_error("Public Server Pool Prometheus Query Failed", query=query, exception=exc)
		return None

	if not response.ok:
		log_error(
			"Public Server Pool Prometheus Query Failed",
			query=query,
			status_code=response.status_code,
			response=data,
		)
		return None

	if data.get("status") != "success":
		log_error("Public Server Pool Prometheus Query Failed", query=query, response=data)
		return None

	return data.get("data", {}).get("result")


def _send_public_server_pool_health_alert(server_issues: dict[str, list[str]]) -> None:
	if not server_issues:
		return

	affected_servers = sorted(server_issues)
	header_lines = [
		f"**Public Server Pool Health Alerts** - {len(affected_servers)}",
		"",
		"Thresholds: RAM utilization > 80%, CPU utilization > 50%, OOM kills in the last hour > 4",
		"",
	]
	table_header = [
		"| Server | Health Issues |",
		"| --- | --- |",
	]

	table_rows = []
	for server in affected_servers:
		issues = "<br>".join(_escape_markdown_table_cell(issue) for issue in server_issues[server])
		table_rows.append(f"| {_escape_markdown_table_cell(server)} | {issues} |")

	send_raven_message(
		"\n".join(header_lines + table_header + table_rows).strip(), RAVEN_SERVER_ALERTS_CHANNEL
	)


def _send_low_disk_alert(
	selected_site_servers: set[str],
	metrics: PublicServerHealthMetrics,
) -> None:
	"""Alert when new sites go to a server that is low on disk.

	The disk of these servers does not grow on demand. Add a server in the
	cluster instead of a move to a larger plan.
	"""
	available_disk_bytes = metrics["available_disk_bytes"]
	available_disk_ratio = metrics["available_disk_ratio"]
	low_disk_servers = sorted(
		server
		for server in selected_site_servers
		if server in available_disk_bytes
		and (
			available_disk_bytes[server] < MINIMUM_SITE_DISK_BYTES
			or available_disk_ratio.get(server, 1.0) < MINIMUM_SITE_DISK_RATIO
		)
	)
	if not low_disk_servers:
		return

	minimum_disk_gib = MINIMUM_SITE_DISK_BYTES / 1024**3
	header_lines = [
		f"**Public Server Pool Disk Alerts** - {len(low_disk_servers)}",
		"",
		"New sites go to these servers, but they are low on disk. Add a server in the cluster.",
		f"Thresholds: free disk < {minimum_disk_gib:.0f} GiB, or free disk < "
		f"{MINIMUM_SITE_DISK_RATIO * 100:.0f}% of the volume",
		"",
		"| Server | Free disk | Free |",
		"| --- | --- | --- |",
	]

	table_rows = [
		f"| {_escape_markdown_table_cell(server)} "
		f"| {available_disk_bytes[server] / 1024**3:.2f} GiB "
		f"| {available_disk_ratio.get(server, 0.0) * 100:.2f}% |"
		for server in low_disk_servers
	]

	send_raven_message("\n".join(header_lines + table_rows).strip(), RAVEN_SERVER_ALERTS_CHANNEL)


def _escape_markdown_table_cell(value: str) -> str:
	return value.replace("|", "\\|").replace("\n", "<br>")


def _create_no_suitable_servers_incident(
	fallback_servers_by_cluster: dict[str, str],
	metrics: PublicServerHealthMetrics,
) -> None:
	if not fallback_servers_by_cluster:
		return

	subject = "No suitable public servers found"
	if _open_public_server_pool_incident_exists(subject):
		return

	description_lines = [
		"Public server pool health check found clusters without a suitable healthy server.",
		"Least-bad fallback servers were selected so scheduling can continue.",
		"",
		"Fallback servers:",
	]

	for cluster, selected_server in sorted(fallback_servers_by_cluster.items()):
		description_lines.extend(
			[
				"",
				f"Cluster: {cluster}",
				f"Selected fallback server: {selected_server}",
				"Health issues:",
			]
		)
		issues = _get_public_server_health_issues(selected_server, metrics)
		if issues:
			description_lines.extend(f"- {issue}" for issue in issues)
		else:
			description_lines.append("- No hard RAM or CPU issue was recorded for the selected fallback.")

	description_lines.extend(
		[
			"",
			"Action required: provision new servers in these clusters or reduce load on existing servers.",
		]
	)

	incident_values = {
		"doctype": "Incident",
		"type": "Server Down",
		"subject": subject,
		"description": "\n".join(description_lines),
	}

	if len(fallback_servers_by_cluster) == 1:
		cluster, selected_server = next(iter(fallback_servers_by_cluster.items()))
		incident_values["server"] = selected_server
		incident_values["cluster"] = cluster

	_insert_public_server_pool_incident(
		incident_values,
		"Failed to create no-suitable-server public pool incident",
		fallback_servers_by_cluster=fallback_servers_by_cluster,
	)


def _insert_public_server_pool_incident(
	incident_values: dict,
	error_title: str,
	**log_context,
) -> None:
	try:
		incident = frappe.get_doc(incident_values)
		incident.insert(ignore_permissions=True)
	except Exception as exc:
		log_error(error_title, exception=exc, **log_context)


def _open_public_server_pool_incident_exists(subject: str, cluster: str | None = None) -> bool:
	filters = {
		"subject": subject,
		"status": ["not in", ["Resolved", "Auto-Resolved", "Press-Resolved"]],
	}
	if cluster:
		filters["cluster"] = cluster
	return bool(frappe.db.exists("Incident", filters))
