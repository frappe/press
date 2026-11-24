# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from collections import Counter
from contextlib import suppress
from typing import TypedDict

import frappe
import requests
from frappe.query_builder.functions import Count, IfNull
from frappe.utils.password import get_decrypted_password

from press.utils import log_error
from press.utils.raven import send_raven_message

RAVEN_SERVER_ALERTS_CHANNEL = "frappe-cloud-server-alerts"
PROMETHEUS_REGEX_META_CHAR_PATTERN = re.compile(r"([\\.^$*+?()[\]{}|])")

# No dedicated signup channel yet, so signup alerts land with the other alerts
RAVEN_SIGNUP_ALERTS_CHANNEL = RAVEN_SERVER_ALERTS_CHANNEL
SIGNUP_ALERT_WINDOW_HOURS = 1
# Time a signup gets to read the mail and finish before it counts as incomplete
SIGNUP_COMPLETION_GRACE_HOURS = 1
TEST_SIGNUP_EMAIL_PATTERN = "fc-signup-test%"
TRIAL_SIGNUP_FAILURE_RATIO_THRESHOLD = 0.3
TRIAL_SIGNUP_MINIMUM_COUNT = 5
# Most people who ask for a verification mail never finish, so only a near-total
# stall means signups are broken rather than merely abandoned
INCOMPLETE_SIGNUP_RATIO_THRESHOLD = 0.9
INCOMPLETE_SIGNUP_MINIMUM_COUNT = 10
OOM_KILLS_ALERT_THRESHOLD = 30
DATABASE_SERVER_DISK_USED_ALERT_THRESHOLD = 0.91
# A halted database server misses its ~27 scheduled jobs a day; healthy servers stay under 15
STUCK_AGENT_JOBS_ALERT_THRESHOLD = 15
STUCK_AGENT_JOBS_WINDOW_HOURS = 24
# Skip young jobs, so a deploy's burst of queued site jobs doesn't count
STUCK_AGENT_JOBS_MINIMUM_AGE_MINUTES = 30
# A public server has room for more sites while it keeps this much memory, CPU and disk free.
# The disk line sits below the alert threshold: a site that lands here brings its data with it.
FREE_MEMORY_RATIO_FOR_NEW_SITES = 0.2
IDLE_CPU_RATIO_FOR_NEW_SITES = 0.5
DISK_USED_RATIO_FOR_NEW_SITES = 0.85
SERVER_DISK_USED_ALERT_THRESHOLD = 0.9
# Older failures are history: the group has been rebuilt or left alone on purpose since
PUBLIC_GROUP_BUILD_FAILURE_WINDOW_DAYS = 7


class PublicServerHealthMetrics(TypedDict):
	available_memory_bytes: dict[str, float]
	available_memory_ratio: dict[str, float]
	cpu_idle_ratio: dict[str, float]
	disk_used_ratio: dict[str, float]
	oom_kills: dict[str, float]


class PublicServerPoolDecision(TypedDict):
	selected_bench_servers: set[str]
	selected_site_servers: set[str]
	servers_with_decision: set[str]
	server_issues: dict[str, list[str]]
	fallback_servers_by_cluster: dict[str, str]


class ServerStuckAgentJobs(TypedDict):
	server_type: str
	server: str
	undelivered: int
	pending: int
	halted: bool


class ServerCapacity(TypedDict):
	name: str
	free_memory_percent: float
	idle_cpu_percent: float
	free_disk_percent: float


class FailedPublicGroupBuild(TypedDict):
	group: str
	title: str
	build: str
	error_key: str | None
	failed_step: str | None


class SignupFailureRate(TypedDict):
	label: str
	failed: int
	total: int
	ratio_threshold: float
	minimum_count: int
	breakdown: dict[str, int]
	link: str


def monitor_server_and_refresh_new_bench_and_site_server_pool() -> None:
	"""Refresh `use_for_new_benches` and `use_for_new_sites` flags for public clusters
	1. Consider active, public primary servers for each cluster
	2. Fetch memory, CPU and OOM-kill health for all servers in bulk from Prometheus
	3. Prefer healthy servers on the lowest-priced plan
	4. Fall back to the least-bad server when a cluster has no healthy candidates
	"""
	server_names, servers_by_cluster = _get_public_primary_servers_by_cluster()
	if not server_names:
		return

	metrics = _get_public_server_health_metrics(server_names)
	if not metrics:
		return

	server_plan_prices = _get_public_server_plan_prices(server_names)
	pool_decision = _get_public_server_pool_decision(servers_by_cluster, metrics, server_plan_prices)
	_apply_public_server_pool_decision(server_names, pool_decision)
	server_issues = (
		pool_decision["server_issues"]
		| _get_public_database_server_disk_issues()
		| _get_excluded_public_server_disk_issues()
	)
	_send_public_server_pool_health_alert(server_issues)
	_create_no_suitable_servers_incident(pool_decision["fallback_servers_by_cluster"], metrics)


def _get_public_primary_servers_by_cluster() -> tuple[list[str], dict[str, list[str]]]:
	servers = frappe.get_all(
		"Server",
		filters={"status": "Active", "is_primary": True, "public": True, "exclude_for_scheduling": False},
		fields=["name", "cluster"],
	)
	server_names = [server.name for server in servers]
	servers_by_cluster: dict[str, list[str]] = {}
	for server in servers:
		servers_by_cluster.setdefault(server.cluster, []).append(server.name)
	return server_names, servers_by_cluster


def _get_public_server_plan_prices(server_names: list[str]) -> dict[str, float]:
	servers = frappe.get_all(
		"Server",
		filters={"name": ["in", server_names]},
		fields=["name", "plan"],
	)
	plan_names = list({server.plan for server in servers if server.plan})
	if not plan_names:
		return {}

	plans = frappe.get_all(
		"Server Plan",
		filters={"name": ["in", plan_names]},
		fields=["name", "price_usd"],
	)
	prices_by_plan = {plan.name: float(plan.price_usd) for plan in plans if plan.price_usd is not None}
	return {server.name: prices_by_plan[server.plan] for server in servers if server.plan in prices_by_plan}


def _get_public_server_pool_decision(
	servers_by_cluster: dict[str, list[str]],
	metrics: PublicServerHealthMetrics,
	server_plan_prices: dict[str, float] | None = None,
) -> PublicServerPoolDecision:
	server_plan_prices = server_plan_prices or {}
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

		healthy_servers = [
			server
			for server in candidates
			if ram_available_ratio[server] >= FREE_MEMORY_RATIO_FOR_NEW_SITES
			and cpu_idle_ratio[server] >= IDLE_CPU_RATIO_FOR_NEW_SITES
		]
		decision["servers_with_decision"].update(cluster_servers)

		if healthy_servers:
			preferred_servers = _get_lowest_price_servers(healthy_servers, server_plan_prices)
			decision["selected_bench_servers"].add(
				max(
					sorted(preferred_servers),
					key=lambda server: _get_bench_pool_score(server, metrics),
				)
			)
			decision["selected_site_servers"].add(
				max(
					sorted(preferred_servers),
					key=lambda server: _get_site_pool_score(server, metrics),
				)
			)
			continue

		selected_server = max(
			sorted(candidates), key=lambda server: _get_least_bad_pool_score(server, metrics)
		)
		decision["selected_bench_servers"].add(selected_server)
		decision["selected_site_servers"].add(selected_server)
		decision["fallback_servers_by_cluster"][cluster] = selected_server

	alert_servers = {server for servers in servers_by_cluster.values() for server in servers}
	for server in alert_servers:
		issues = _get_public_server_alert_issues(server, metrics)
		if issues:
			decision["server_issues"][server] = issues

	return decision


def _get_lowest_price_servers(servers: list[str], server_plan_prices: dict[str, float]) -> list[str]:
	priced_servers = [server for server in servers if server in server_plan_prices]
	if not priced_servers:
		return servers

	lowest_price = min(server_plan_prices[server] for server in priced_servers)
	return [server for server in priced_servers if server_plan_prices[server] == lowest_price]


def _get_public_server_placement_issues(server: str, metrics: PublicServerHealthMetrics) -> list[str]:
	issues = []
	ram_utilization = 1 - metrics["available_memory_ratio"][server]
	cpu_utilization = 1 - metrics["cpu_idle_ratio"][server]

	if ram_utilization > 0.8:
		issues.append(f"RAM utilization: {ram_utilization * 100:.2f}%")
	if cpu_utilization > 0.5:
		issues.append(f"CPU utilization: {cpu_utilization * 100:.2f}%")

	return issues


def _get_public_server_alert_issues(server: str, metrics: PublicServerHealthMetrics) -> list[str]:
	issues = []
	ram_available_ratio = metrics["available_memory_ratio"].get(server)
	cpu_idle_ratio = metrics["cpu_idle_ratio"].get(server)
	disk_used_ratio = metrics["disk_used_ratio"].get(server, 0.0)
	oom_kills = metrics["oom_kills"].get(server, 0.0)

	if ram_available_ratio is not None and 1 - ram_available_ratio > 0.9:
		issues.append(f"RAM utilization: {(1 - ram_available_ratio) * 100:.2f}%")
	if cpu_idle_ratio is not None and 1 - cpu_idle_ratio > 0.5:
		issues.append(f"CPU utilization: {(1 - cpu_idle_ratio) * 100:.2f}%")
	if disk_used_ratio > SERVER_DISK_USED_ALERT_THRESHOLD:
		issues.append(f"Disk utilization: {disk_used_ratio * 100:.2f}%")
	if oom_kills > OOM_KILLS_ALERT_THRESHOLD:
		issues.append(f"OOM kills: {max(1, round(oom_kills))}")

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
	failed_check_count = len(_get_public_server_placement_issues(server, metrics))
	return (
		-failed_check_count,
		metrics["cpu_idle_ratio"].get(server, 0.0),
		metrics["available_memory_ratio"].get(server, 0.0),
		metrics["available_memory_bytes"].get(server, 0.0),
	)


def get_public_servers_with_free_capacity(server_names: list[str]) -> list[ServerCapacity]:
	"""Servers that have room for another site, the one with the most room first."""
	metrics = _get_public_server_health_metrics(server_names)
	if not metrics:
		frappe.throw("Server capacity is unavailable right now. Please try again in a few minutes.")
		return []

	servers = [server for server in server_names if _has_free_capacity_for_sites(server, metrics)]
	servers.sort(key=lambda server: _get_site_pool_score(server, metrics), reverse=True)
	return [_get_server_capacity(server, metrics) for server in servers]


def _has_free_capacity_for_sites(server: str, metrics: PublicServerHealthMetrics) -> bool:
	return (
		metrics["available_memory_ratio"].get(server, 0.0) >= FREE_MEMORY_RATIO_FOR_NEW_SITES
		and metrics["cpu_idle_ratio"].get(server, 0.0) >= IDLE_CPU_RATIO_FOR_NEW_SITES
		and metrics["disk_used_ratio"].get(server, 0.0) < DISK_USED_RATIO_FOR_NEW_SITES
	)


def _get_server_capacity(server: str, metrics: PublicServerHealthMetrics) -> ServerCapacity:
	return {
		"name": server,
		"free_memory_percent": round(metrics["available_memory_ratio"].get(server, 0.0) * 100, 1),
		"idle_cpu_percent": round(metrics["cpu_idle_ratio"].get(server, 0.0) * 100, 1),
		"free_disk_percent": round((1 - metrics["disk_used_ratio"].get(server, 0.0)) * 100, 1),
	}


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


def _get_public_server_health_metrics(server_names: list[str]) -> PublicServerHealthMetrics | None:
	"""Fetch placement and alerting metrics for public servers from Prometheus."""
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
	disk_used_ratio_query = _get_disk_used_ratio_query(instance_matcher)
	oom_kills_query = (
		f'sum by (instance) (increase(node_vmstat_oom_kill{{instance=~"^({instance_matcher})$", '
		f'job="node"}}[60m])) > {OOM_KILLS_ALERT_THRESHOLD}'
	)

	available_memory_bytes_results = _query_prometheus_vector(available_memory_bytes_query, url, auth)
	available_memory_ratio_results = _query_prometheus_vector(available_memory_ratio_query, url, auth)
	cpu_idle_ratio_results = _query_prometheus_vector(cpu_idle_ratio_query, url, auth)
	disk_used_ratio_results = _query_prometheus_vector(disk_used_ratio_query, url, auth)
	oom_kills_results = _query_prometheus_vector(oom_kills_query, url, auth)

	if (
		available_memory_bytes_results is None
		or available_memory_ratio_results is None
		or cpu_idle_ratio_results is None
	):
		return None

	return {
		"available_memory_bytes": _build_public_server_metric_map(
			server_names, available_memory_bytes_results
		),
		"available_memory_ratio": _build_public_server_metric_map(
			server_names, available_memory_ratio_results
		),
		"cpu_idle_ratio": _build_public_server_metric_map(server_names, cpu_idle_ratio_results),
		"disk_used_ratio": _build_public_server_metric_map(
			server_names, disk_used_ratio_results, default=0.0
		),
		"oom_kills": _build_public_server_metric_map(server_names, oom_kills_results, default=0.0),
	}


def _get_disk_used_ratio_query(instance_matcher: str, mountpoint: str = "/") -> str:
	return (
		f'1 - (node_filesystem_avail_bytes{{instance=~"^({instance_matcher})$", job="node", '
		f'device!~"rootfs", mountpoint="{mountpoint}"}} / node_filesystem_size_bytes{{'
		f'instance=~"^({instance_matcher})$", job="node", device!~"rootfs", mountpoint="{mountpoint}"}})'
	)


def _get_excluded_public_server_disk_issues() -> dict[str, list[str]]:
	"""Excluded servers skip the pool check, but still host benches and get deploys."""
	servers = frappe.get_all(
		"Server",
		filters={"status": "Active", "is_primary": True, "public": True, "exclude_for_scheduling": True},
		pluck="name",
	)
	prometheus_connection = _get_public_server_pool_prometheus_connection()
	if not (servers and prometheus_connection):
		return {}

	instance_matcher = "|".join(_escape_prometheus_regex_literal(name) for name in servers)
	results = _query_prometheus_vector(_get_disk_used_ratio_query(instance_matcher), *prometheus_connection)
	return {
		server: [f"Disk utilization: {ratio * 100:.2f}%"]
		for server, ratio in _build_public_server_metric_map(servers, results).items()
		if ratio > 0.9
	}


def _get_public_database_server_disk_issues() -> dict[str, list[str]]:
	prometheus_connection = _get_public_server_pool_prometheus_connection()
	if not prometheus_connection:
		return {}

	disk_used_ratios: dict[str, float] = {}
	for mountpoint, server_names in _get_public_database_servers_by_data_mountpoint().items():
		instance_matcher = "|".join(_escape_prometheus_regex_literal(name) for name in server_names)
		query = _get_disk_used_ratio_query(instance_matcher, mountpoint)
		results = _query_prometheus_vector(query, *prometheus_connection)
		disk_used_ratios |= _build_public_server_metric_map(server_names, results)

	return {
		server: [f"Disk utilization: {ratio * 100:.2f}%"]
		for server, ratio in disk_used_ratios.items()
		if ratio > DATABASE_SERVER_DISK_USED_ALERT_THRESHOLD
	}


def _get_public_database_servers_by_data_mountpoint() -> dict[str, list[str]]:
	"""Servers with a data volume keep MariaDB files off the root disk."""
	from press.press.doctype.server.server import MARIADB_DATA_MNT_POINT

	servers = frappe.get_all(
		"Database Server",
		filters={"status": "Active", "public": True},
		fields=["name", "has_data_volume"],
	)
	servers_by_mountpoint: dict[str, list[str]] = {}
	for server in servers:
		mountpoint = MARIADB_DATA_MNT_POINT if server.has_data_volume else "/"
		servers_by_mountpoint.setdefault(mountpoint, []).append(server.name)
	return servers_by_mountpoint


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
	thresholds = (
		"Thresholds: RAM utilization > 90%, CPU utilization > 50%, Disk utilization > 90% "
		f"(database servers > {DATABASE_SERVER_DISK_USED_ALERT_THRESHOLD * 100:.0f}%), "
		f"OOM kills > {OOM_KILLS_ALERT_THRESHOLD}"
	)
	header_lines = [
		f"**Public Server Pool Health Alerts** - {len(affected_servers)}",
		"",
		thresholds,
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
		issues = _get_public_server_placement_issues(selected_server, metrics)
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


def alert_on_failing_signups() -> None:
	"""Alert when a large share of recent signups failed.

	Two independent signals: product trial signups that errored out, and signups that
	never became a team. Each is compared against its own ratio, over a volume floor,
	so a single person walking away at 3am doesn't page anyone.
	"""
	rates = [_get_trial_signup_failure_rate(), _get_incomplete_signup_rate()]
	breached = [rate for rate in rates if _breaches_signup_failure_threshold(rate)]
	if breached:
		_send_signup_failure_alert(breached)


def _get_trial_signup_failure_rate() -> SignupFailureRate:
	"""Product trial signups that settled in the window - errored out against site created.

	Windowed on when the status last changed, not on creation: a request that took three
	hours to fail is a failure this hour, and windowing on creation would drop it for
	good, exactly when provisioning is slow enough to be the outage worth alerting on.
	Not on `modified` either - a later write, like the accessibility check at login, would
	drag a long-settled request into this window and alert on an outcome from yesterday.
	"""
	requests = frappe.get_all(
		"Product Trial Request",
		filters={
			"status_updated_on": (
				">",
				frappe.utils.add_to_date(None, hours=-SIGNUP_ALERT_WINDOW_HOURS),
			),
			"status": ("in", ["Error", "Site Created"]),
			"owner": ("not like", TEST_SIGNUP_EMAIL_PATTERN),
		},
		fields=["status", "product_trial"],
	)
	failed = [request for request in requests if request.status == "Error"]
	return {
		"label": "Product trial signups that errored out",
		"failed": len(failed),
		"total": len(requests),
		"ratio_threshold": TRIAL_SIGNUP_FAILURE_RATIO_THRESHOLD,
		"minimum_count": TRIAL_SIGNUP_MINIMUM_COUNT,
		"breakdown": Counter(request.product_trial or "Unknown" for request in failed),
		"link": frappe.utils.get_url("/app/product-trial-request?status=Error"),
	}


def _get_incomplete_signup_rate() -> SignupFailureRate:
	"""Signups that asked for verification but never ended up with a team."""
	emails = set(_get_signup_emails_past_grace_period())
	teams = frappe.get_all("Team", filters={"user": ("in", list(emails))}, pluck="user") if emails else []
	return {
		"label": "Signups that never became a team",
		"failed": len(emails - set(teams)),
		"total": len(emails),
		"ratio_threshold": INCOMPLETE_SIGNUP_RATIO_THRESHOLD,
		"minimum_count": INCOMPLETE_SIGNUP_MINIMUM_COUNT,
		"breakdown": {},
		"link": frappe.utils.get_url("/app/account-request"),
	}


def _get_signup_emails_past_grace_period() -> list[str]:
	"""Emails from signup requests old enough to have finished, but no older than the window.

	Team invites are left out - a member joining an existing team is a different funnel.
	"""
	window_end = frappe.utils.add_to_date(None, hours=-SIGNUP_COMPLETION_GRACE_HOURS)
	window_start = frappe.utils.add_to_date(window_end, hours=-SIGNUP_ALERT_WINDOW_HOURS)
	return frappe.get_all(
		"Account Request",
		filters={
			"creation": ("between", [window_start, window_end]),
			"invited_by": ("is", "not set"),
			"email": ("not like", TEST_SIGNUP_EMAIL_PATTERN),
		},
		pluck="email",
	)


def _breaches_signup_failure_threshold(rate: SignupFailureRate) -> bool:
	if rate["total"] < rate["minimum_count"]:
		return False
	return rate["failed"] / rate["total"] > rate["ratio_threshold"]


def _send_signup_failure_alert(rates: list[SignupFailureRate]) -> None:
	lines = [f"**Signup Failure Alerts** - {len(rates)}", ""]
	for rate in rates:
		lines.append(_describe_signup_failure_rate(rate))
		lines.extend(f"- {name}: {count}" for name, count in sorted(rate["breakdown"].items()))
		lines.append("")

	send_raven_message("\n".join(lines).strip(), RAVEN_SIGNUP_ALERTS_CHANNEL)


def _describe_signup_failure_rate(rate: SignupFailureRate) -> str:
	failure_ratio = rate["failed"] / rate["total"] * 100
	return (
		f"[{rate['label']}]({rate['link']}): {rate['failed']} of {rate['total']} "
		f"({failure_ratio:.2f}%) in the last {SIGNUP_ALERT_WINDOW_HOURS}h, "
		f"threshold {rate['ratio_threshold'] * 100:.0f}%"
	)


def alert_on_servers_with_stuck_agent_jobs() -> None:
	"""Alert when active servers outside archived regions hold many agent jobs that never ran.

	Undelivered jobs pile up on a halted or unreachable server, pending ones on a stuck agent.
	"""
	servers = _get_servers_with_stuck_agent_jobs()
	if servers:
		_send_stuck_agent_jobs_alert(servers)


def _get_servers_with_stuck_agent_jobs() -> list[ServerStuckAgentJobs]:
	counts = _count_stuck_agent_jobs_by_server()
	over_threshold = [row for row in counts if _total_stuck_jobs(row) >= STUCK_AGENT_JOBS_ALERT_THRESHOLD]
	halt_flags = _get_halt_flags_of_active_servers({_server_key(row) for row in over_threshold})
	servers = [row for row in over_threshold if _server_key(row) in halt_flags]
	for row in servers:
		row["halted"] = halt_flags[_server_key(row)]
	return sorted(servers, key=_total_stuck_jobs, reverse=True)


def _get_stuck_agent_job_counts() -> list[frappe._dict]:
	# frappe.get_all on fc-prod has no dict aggregates, so count with frappe.qb
	now = frappe.utils.now_datetime()
	window_start = frappe.utils.add_to_date(now, hours=-STUCK_AGENT_JOBS_WINDOW_HOURS)
	window_end = frappe.utils.add_to_date(now, minutes=-STUCK_AGENT_JOBS_MINIMUM_AGE_MINUTES)
	AgentJob = frappe.qb.DocType("Agent Job")
	return (
		frappe.qb.from_(AgentJob)
		.select(AgentJob.server_type, AgentJob.server, AgentJob.status, Count("*").as_("jobs"))
		.where(AgentJob.status.isin(["Undelivered", "Pending"]))
		.where(AgentJob.creation.between(window_start, window_end))
		.where(IfNull(AgentJob.server, "") != "")
		.where(IfNull(AgentJob.server_type, "") != "")
		.groupby(AgentJob.server_type, AgentJob.server, AgentJob.status)
		.run(as_dict=True)
	)


def _count_stuck_agent_jobs_by_server() -> list[ServerStuckAgentJobs]:
	counts: dict[tuple[str, str], ServerStuckAgentJobs] = {}
	for row in _get_stuck_agent_job_counts():
		key = (row.server_type, row.server)
		counts.setdefault(
			key, {"server_type": key[0], "server": key[1], "undelivered": 0, "pending": 0, "halted": False}
		)
		if row.status == "Pending":
			counts[key]["pending"] = row.jobs
		else:
			counts[key]["undelivered"] = row.jobs
	return list(counts.values())


def _get_halt_flags_of_active_servers(servers: set[tuple[str, str]]) -> dict[tuple[str, str], bool]:
	halt_flags = {}
	archived_clusters = frappe.get_all("Cluster", filters={"status": "Archived"}, pluck="name")
	for server_type in {server_type for server_type, _ in servers}:
		names = [name for doctype, name in servers if doctype == server_type]
		meta = frappe.get_meta(server_type)
		filters = {"name": ("in", names), "status": "Active"}
		# Servers in an archived region can't be reached, so their jobs pile up for good
		if archived_clusters and meta.has_field("cluster"):
			filters["cluster"] = ("not in", archived_clusters)
		# Registry, log and other server types have no halt flag
		fields = ["name", "halt_agent_jobs"] if meta.has_field("halt_agent_jobs") else ["name"]
		for server in frappe.get_all(server_type, filters=filters, fields=fields):
			halt_flags[(server_type, server.name)] = bool(server.get("halt_agent_jobs"))
	return halt_flags


def _server_key(row: ServerStuckAgentJobs) -> tuple[str, str]:
	return (row["server_type"], row["server"])


def _total_stuck_jobs(row: ServerStuckAgentJobs) -> int:
	return row["undelivered"] + row["pending"]


def _send_stuck_agent_jobs_alert(servers: list[ServerStuckAgentJobs]) -> None:
	criteria = (
		f"Undelivered + Pending jobs created in the last {STUCK_AGENT_JOBS_WINDOW_HOURS}h "
		f"(older than {STUCK_AGENT_JOBS_MINIMUM_AGE_MINUTES}m), threshold {STUCK_AGENT_JOBS_ALERT_THRESHOLD}"
	)
	lines = [
		f"**Servers With Stuck Agent Jobs** - {len(servers)}",
		"",
		criteria,
		"",
		"| Server | Type | Undelivered | Pending | Agent Jobs Halted |",
		"| --- | --- | --- | --- | --- |",
	]
	lines.extend(_describe_server_with_stuck_agent_jobs(row) for row in servers)
	send_raven_message("\n".join(lines), RAVEN_SERVER_ALERTS_CHANNEL)


def _describe_server_with_stuck_agent_jobs(row: ServerStuckAgentJobs) -> str:
	link = frappe.utils.get_url_to_form(row["server_type"], row["server"])
	halted = "Yes" if row["halted"] else "No"
	return (
		f"| [{row['server']}]({link}) | {row['server_type']} | {row['undelivered']} "
		f"| {row['pending']} | {halted} |"
	)


def alert_on_failed_public_group_builds() -> None:
	"""Alert once for each public bench group whose latest build failed.

	A failed build only notifies the group's team on the dashboard, and for public groups
	that team is us, so a broken signup or shared bench group can sit unnoticed for days.
	"""
	builds = [
		build for build in _get_failed_public_group_builds() if not _was_build_failure_alerted(build["build"])
	]
	if not builds:
		return

	_send_failed_public_group_builds_alert(builds)
	for build in builds:
		_mark_build_failure_alerted(build["build"])


def _get_failed_public_group_builds() -> list[FailedPublicGroupBuild]:
	failed: list[FailedPublicGroupBuild] = []
	for group in frappe.get_all(
		"Release Group", filters={"public": 1, "enabled": 1}, fields=["name", "title"]
	):
		build = _get_latest_build_of_group(group.name)
		if build and build.status == "Failure":
			failed.append(
				{
					"group": group.name,
					"title": group.title,
					"build": build.name,
					"error_key": build.error_key,
					"failed_step": _get_failed_build_step(build.name),
				}
			)
	return failed


def _get_latest_build_of_group(group: str) -> frappe._dict | None:
	# A retry is a newer build, so a failure that is being retried is not the latest
	window_start = frappe.utils.add_days(None, -PUBLIC_GROUP_BUILD_FAILURE_WINDOW_DAYS)
	builds = frappe.get_all(
		"Deploy Candidate Build",
		filters={"group": group, "creation": (">", window_start)},
		fields=["name", "status", "error_key"],
		order_by="creation desc",
		limit=1,
	)
	return builds[0] if builds else None


def _get_failed_build_step(build: str) -> str | None:
	steps = frappe.get_all(
		"Deploy Candidate Build Step",
		filters={"parenttype": "Deploy Candidate Build", "parent": build, "status": "Failure"},
		fields=["stage", "step"],
		order_by="idx asc",
		limit=1,
	)
	return f"{steps[0].stage} / {steps[0].step}" if steps else None


def _build_failure_alert_cache_key(build: str) -> str:
	return f"public_group_build_failure_alerted:{build}"


def _was_build_failure_alerted(build: str) -> bool:
	return bool(frappe.cache.get_value(_build_failure_alert_cache_key(build)))


def _mark_build_failure_alerted(build: str) -> None:
	expires_in_sec = PUBLIC_GROUP_BUILD_FAILURE_WINDOW_DAYS * 24 * 60 * 60
	frappe.cache.set_value(_build_failure_alert_cache_key(build), True, expires_in_sec=expires_in_sec)


def _send_failed_public_group_builds_alert(builds: list[FailedPublicGroupBuild]) -> None:
	lines = [
		f"**Public Bench Group Builds Failed** - {len(builds)}",
		"",
		"| Bench Group | Build | Error | Failed Step |",
		"| --- | --- | --- | --- |",
	]
	lines.extend(_describe_failed_public_group_build(build) for build in builds)
	send_raven_message("\n".join(lines), RAVEN_SERVER_ALERTS_CHANNEL)


def _describe_failed_public_group_build(build: FailedPublicGroupBuild) -> str:
	group_link = frappe.utils.get_url_to_form("Release Group", build["group"])
	build_link = frappe.utils.get_url_to_form("Deploy Candidate Build", build["build"])
	title = _escape_markdown_table_cell(build["title"] or build["group"])
	error = _escape_markdown_table_cell(build["error_key"] or "-")
	step = _escape_markdown_table_cell(build["failed_step"] or "-")
	return f"| [{title}]({group_link}) | [{build['build']}]({build_link}) | {error} | {step} |"
