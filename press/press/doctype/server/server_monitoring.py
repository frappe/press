# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from collections import Counter
from contextlib import suppress
from typing import TypedDict

import frappe
import requests
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


class PublicServerHealthMetrics(TypedDict):
	available_memory_bytes: dict[str, float]
	available_memory_ratio: dict[str, float]
	cpu_idle_ratio: dict[str, float]
	oom_kills: dict[str, float]


class PublicServerPoolDecision(TypedDict):
	selected_bench_servers: set[str]
	selected_site_servers: set[str]
	servers_with_decision: set[str]
	server_issues: dict[str, list[str]]
	fallback_servers_by_cluster: dict[str, str]


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
	3. Prefer healthy servers, and fall back to the least-bad server when a cluster has no healthy candidates
	"""
	server_names, servers_by_cluster = _get_public_primary_servers_by_cluster()
	if not server_names:
		return

	metrics = _get_public_server_health_metrics(server_names)
	if not metrics:
		return

	pool_decision = _get_public_server_pool_decision(servers_by_cluster, metrics)
	_apply_public_server_pool_decision(server_names, pool_decision)
	_send_public_server_pool_health_alert(pool_decision["server_issues"])
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
			decision["selected_site_servers"].add(
				max(sorted(healthy_servers), key=lambda server: _get_site_pool_score(server, metrics))
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


def _get_public_server_health_metrics(server_names: list[str]) -> PublicServerHealthMetrics | None:
	"""Fetch memory, CPU and kernel OOM-kill metrics for public servers from Prometheus."""
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

	return {
		"available_memory_bytes": _build_public_server_metric_map(
			server_names, available_memory_bytes_results
		),
		"available_memory_ratio": _build_public_server_metric_map(
			server_names, available_memory_ratio_results
		),
		"cpu_idle_ratio": _build_public_server_metric_map(server_names, cpu_idle_ratio_results),
		"oom_kills": _build_public_server_metric_map(server_names, oom_kills_results, default=0.0),
	}


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
	"""
	requests = frappe.get_all(
		"Product Trial Request",
		filters={
			"modified": (">", frappe.utils.add_to_date(None, hours=-SIGNUP_ALERT_WINDOW_HOURS)),
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
