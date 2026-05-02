# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Literal

import frappe
from frappe.utils.data import cint
from frappe.utils.file_manager import save_file
from frappe.utils.synchronization import filelock
from playwright.sync_api import Page, sync_playwright

from press.api.server import prometheus_query

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.incident.incident import Incident
	from press.press.doctype.monitor_server.monitor_server import MonitorServer
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.server.server import Server


# Heuristic thresholds used while categorising an incident.
HIGH_LOAD_FACTOR = 3  # load average > 3 * vCPU is considered high
CPU_BUSY_THRESHOLD_PERCENT = 70
NO_DATA_SENTINEL = -1

SITE_PROBE_STATUS_CODE_MAPPING = {
	200: "Online",
	401: "Unauthorized",
	402: "Suspended",
	403: "Unauthorized",
	404: "Site Not Found",
	500: "Internal Error",
	502: "Down Bench",
	504: "Timeout",
}


class IncidentAnalysis:
	def __init__(self, incident: Incident):
		self.incident = incident

	@cached_property
	def monitor_server(self) -> MonitorServer:
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		if not (monitor_url := press_settings.monitor_server):
			frappe.throw("Monitor Server not set in Press Settings")
		return frappe.get_cached_doc("Monitor Server", monitor_url)

	# region Server Reachability & Collect Metrics
	def check_servers_reachability(self, save: bool = True):
		# Check server status
		server_doc: Server | None = None
		try:
			server_doc = frappe.get_doc("Server", self.incident.server)
			ping_response = server_doc.ping_agent()
			self.incident.server_status = "Reachable" if ping_response else "Unreachable"
		except Exception:
			self.incident.server_status = "Unreachable"

		# Check associated db status
		try:
			db_server_doc: DatabaseServer = frappe.get_doc("Database Server", self.incident.database_server)
			ping_response = db_server_doc.ping_agent()
			self.incident.db_server_status = "Reachable" if ping_response else "Unreachable"
		except Exception:
			self.incident.db_server_status = "Unreachable"

		# If db server is reachable, check if mariadb is reachable through app server
		# DON'T ask database server to check for mariadb health
		# Because, it most of the time will say it's healthy, but external access to db might be down
		if server_doc and self.incident.db_server_status == "Reachable":
			try:
				db_reachable = server_doc.ping_mariadb()
				self.incident.db_server_status = (
					"Reachable - DB Healthy" if db_reachable else "Reachable - DB Unhealthy"
				)
			except Exception:
				self.incident.db_server_status = "Reachable - DB Unhealthy"

		if save:
			self.incident.save()

	def collect_server_stats(self, save: bool = True):
		"""Collect current resource metrics from Prometheus for the app server and
		database server and store them on the incident document."""

		server = self.incident.server
		db_server = self.incident.database_server
		timespan = 60 * 60  # 1hr

		if server:
			self.incident.server_load15 = self.monitor_server.run_promql_scalar(
				f'node_load15{{instance="{server}", job="node"}}', float
			)
			self.incident.server_runnable_state = self.monitor_server.run_promql_scalar(
				f'quantile_over_time(0.95, node_procs_running{{instance="{server}", job="node"}}[{timespan}s])',
				int,
			)
			self.incident.server_disk_iops = self.monitor_server.run_promql_scalar(
				f"quantile_over_time(0.95,"
				f' (sum(irate(node_disk_reads_completed_total{{instance="{server}", job="node"}}[2m]))'
				f' + sum(irate(node_disk_writes_completed_total{{instance="{server}", job="node"}}[2m])))'
				f"[{timespan}s:1m])",
				int,
			)
			self.incident.server_disk_throughput_mbps = self.monitor_server.run_promql_scalar(
				f"quantile_over_time(0.95,"
				f' (sum(irate(node_disk_read_bytes_total{{instance="{server}", job="node"}}[2m]))'
				f' + sum(irate(node_disk_written_bytes_total{{instance="{server}", job="node"}}[2m])))'
				f"[{timespan}s:1m]) / (1024 * 1024)",
				int,
			)

			server_doc: Server = frappe.get_doc("Server", server)
			self.incident.server_free_space_gb = round(
				server_doc.free_space(mountpoint=server_doc.guess_data_disk_mountpoint())
				/ (1024 * 1024 * 1024),
				2,
			)
			self.incident.server_oom_kills = self.monitor_server.run_promql_scalar(
				f'node_vmstat_oom_kill{{instance="{server}", job="node"}}', int
			)

		if db_server:
			self.incident.db_server_load15 = self.monitor_server.run_promql_scalar(
				f'node_load15{{instance="{db_server}", job="node"}}', val_type=float
			)
			self.incident.db_server_disk_iops = self.monitor_server.run_promql_scalar(
				f"quantile_over_time(0.95,"
				f' (sum(irate(node_disk_reads_completed_total{{instance="{db_server}", job="node"}}[2m]))'
				f' + sum(irate(node_disk_writes_completed_total{{instance="{db_server}", job="node"}}[2m])))'
				f"[{timespan}s:1m])",
				int,
			)
			self.incident.db_server_disk_queue = self.monitor_server.run_promql_scalar(
				f"max_over_time("
				f' sum(rate(node_disk_io_time_weighted_seconds_total{{instance="{db_server}", job="node"}}[2m]))'
				f"[{timespan}s:1m])",
				int,
			)
			self.incident.db_server_disk_throughput_mbps = self.monitor_server.run_promql_scalar(
				f"quantile_over_time(0.95,"
				f' (sum(irate(node_disk_read_bytes_total{{instance="{db_server}", job="node"}}[2m]))'
				f' + sum(irate(node_disk_written_bytes_total{{instance="{db_server}", job="node"}}[2m])))'
				f"[{timespan}s:1m]) / (1024 * 1024)",
				int,
			)
			self.incident.db_server_free_memory_mb = self.monitor_server.run_promql_scalar(
				f'node_memory_MemAvailable_bytes{{instance="{db_server}", job="node"}} / (1024 * 1024)',
				int,
			)

			db_server_doc: DatabaseServer = frappe.get_doc("Database Server", db_server)
			self.incident.db_free_space_gb = round(
				db_server_doc.free_space(mountpoint=db_server_doc.guess_data_disk_mountpoint())
				/ (1024 * 1024 * 1024),
				2,
			)

		if save:
			self.incident.save()

	# endregion

	# region Update down sites/benches list with some investigation data

	def refresh_down_sites_benches_list(self, save: bool = True):
		alerts: list[dict[str, str]] = [
			{"bench": item["metric"].get("bench"), "site": item["metric"].get("instance")}
			for item in self.monitor_server.run_promql(
				f'sum by (instance, bench) (ALERTS{{alertname="Sites Down",server="{self.incident.server}"}})'
			)
		]

		down_sites = set(item["site"] for item in alerts if item["site"])
		self._update_down_sites_list(down_sites, save=False)

		down_benches = set(item["bench"] for item in alerts if item["bench"])
		down_sites_count_per_bench = {
			bench: len([item for item in alerts if item["bench"] == bench and item["site"]])
			for bench in down_benches
		}
		self._update_down_benches_list(down_benches, down_sites_count_per_bench, save=False)

		if save:
			self.incident.save()

	def _update_down_sites_list(self, down_sites: set[str], save: bool = True):  # noqa: C901
		self.incident.no_of_total_sites = frappe.db.count(
			"Site", {"server": self.incident.server, "status": "Active", "is_monitoring_disabled": 0}
		)
		self.incident.no_of_down_sites = len(down_sites)

		# Find down sites probes
		down_sites_with_status_code: dict[str, int] = {
			item["metric"]["instance"]: cint(item["value"][-1])
			for item in self.monitor_server.run_promql(
				f"""(
  probe_http_status_code{{job="site", server="{self.incident.server}"}} >= 400
  and probe_http_status_code != 429
)
or on(instance)
(
  probe_success{{job="site", server="{self.incident.server}"}} == 0
)
"""
			)
		}

		# Update the list of down sites table
		for record in self.incident.down_sites:
			if record.site not in down_sites or record.site not in down_sites_with_status_code:
				record.current_http_status = 200
			else:
				record.current_http_status = down_sites_with_status_code.get(record.site, NO_DATA_SENTINEL)

			record.current_status = SITE_PROBE_STATUS_CODE_MAPPING.get(
				record.current_http_status, "Unreachable"
			)
			record.current_status_updated_on = frappe.utils.now_datetime()
			down_sites.discard(record.site)  # remove from set to avoid re-adding

		# Add new down sites in pages of 15.
		# - If the table has fewer than 15 rows, fill up the remaining slots.
		# - If the table is already a full page (multiple of 15) and every row is
		#   back online, prepend a fresh page of 15 at the top so the new incidents
		#   are immediately visible.
		PAGE_SIZE = 15
		existing_count = len(self.incident.down_sites)
		all_existing_back_online = (
			existing_count > 0
			and existing_count % PAGE_SIZE == 0
			and all(r.current_http_status == 200 for r in self.incident.down_sites)
		)
		prepend = all_existing_back_online and bool(down_sites)
		slots = PAGE_SIZE if prepend else max(0, PAGE_SIZE - existing_count)

		for i, site in enumerate(list(down_sites)[:slots]):
			http_status = down_sites_with_status_code.get(site, NO_DATA_SENTINEL)
			status = SITE_PROBE_STATUS_CODE_MAPPING.get(http_status, "Unreachable")
			child = self.incident.append(
				"down_sites",
				{
					"site": site,
					"current_http_status": http_status,
					"current_status": status,
					"current_status_updated_on": frappe.utils.now_datetime(),
					"reported_status": status,
					"reported_http_status": http_status,
				},
			)
			if prepend:
				child.idx = i + 1

		# For down sites with status code 0, check if it's a TLS issue
		tls_issue_candidates = [site for site, code in down_sites_with_status_code.items() if code == 0]
		tls_results = check_tls_issue_bulk(tls_issue_candidates)
		for record in self.incident.down_sites:
			if record.current_http_status != 0 or record.site not in tls_results:
				continue

			record.current_status = "TLS Issue" if tls_results[record.site] else record.current_status
			if (
				record.reported_http_status == record.current_http_status
				and record.reported_status != record.current_status
			):
				record.reported_status = record.current_status

		if save:
			self.incident.save()

	def _update_down_benches_list(
		self, down_benches: set[str], down_sites_count_per_bench: dict[str, int], save: bool = True
	):
		self.incident.no_of_total_benches = frappe.db.count(
			"Bench", {"server": self.incident.server, "status": "Active"}
		)
		self.incident.no_of_down_benches = len(down_benches)

		# Update the list of down benches
		for record in self.incident.down_benches:
			record.current_sites_down = down_sites_count_per_bench.get(record.bench, 0)
			down_benches.discard(record.bench)  # remove from set to avoid re-adding

		# Add new down benches
		for record in down_benches:
			down_sites = down_sites_count_per_bench.get(record, 0)
			self.incident.append(
				"down_benches",
				{
					"bench": record,
					"current_sites_down": down_sites,
					"reported_sites_down": down_sites,
				},
			)

		if save:
			self.incident.save()

	# endregion

	# region Incident Cause categorization

	def find_cause_of_incident(self, save: bool = True):  # noqa: C901
		# First, find out which server is unreachable
		if self.incident.server_status == "Unreachable":
			self._set_affected_resource("Server", save=False)
		elif self.incident.db_server_status in ["Unreachable", "Reachable - DB Unhealthy"]:
			self._set_affected_resource("Database Server", save=False)

		# Check if disk has <512MB free space, the incident is most likely due to that
		if self.incident.server_free_space_gb < 0.5:
			self._set_affected_resource("Server", save=False)
			self.incident.subtype = "Disk Full"
		elif self.incident.db_free_space_gb < 0.5:
			self._set_affected_resource("Database Server", save=False)
			self.incident.subtype = "Disk Full"

		# If we couldn't find anyone of them unreachable or disk issue
		# then, consider resource with high load as affected resource
		if not self.incident.type:
			if self._is_resource_overloaded("Server", str(self.incident.server)):
				self._set_affected_resource("Server", save=False)
			elif self._is_resource_overloaded("Database Server", self.incident.database_server):
				self._set_affected_resource("Database Server", save=False)

		# If subtype not decided, then find dominant CPU mode and set that as subtype
		if not self.incident.subtype and self.incident.resource:
			state, percent = self._find_dominant_cpu_mode(self.incident.resource)
			if state != "idle" and state in ["user", "iowait"] and percent >= CPU_BUSY_THRESHOLD_PERCENT:
				self.incident.subtype = f"High CPU: {state}"

		if save:
			self.incident.save()

	def _set_affected_resource(self, server_type: Literal["Server", "Database Server"], save: bool = True):
		if (server_type == "Server" and self.incident.type != "Server Down") or (
			server_type == "Database Server" and self.incident.type != "Database Down"
		):
			return  # Don't override if already categorized as server down

		self.incident.type = "Server Down" if server_type == "Server" else "Database Down"
		self.incident.resource_type = server_type
		self.incident.resource = (
			self.incident.server if server_type == "Server" else self.incident.database_server
		)
		if save:
			self.incident.save()

	def _find_dominant_cpu_mode(self, instance: str) -> tuple[str, float]:
		"""
		Return the dominant CPU mode and its percentage for the given instance.
		returns ("mode", percent) where mode is one of "user", "idle", "iowait", "softirq", etc.
		"""
		timespan = self.incident.settings.confirmation_threshold_seconds
		cpu_info = prometheus_query(
			f"""avg by (mode)(rate(node_cpu_seconds_total{{instance="{instance}", job="node"}}[{timespan}s])) * 100""",
			lambda x: x["mode"],
			"Asia/Kolkata",
			timespan,
			timespan + 1,
		)["datasets"]
		mode_cpus: dict[str, float] = {x["name"]: x["values"][-1] for x in cpu_info} or {
			"user": NO_DATA_SENTINEL,
			"idle": NO_DATA_SENTINEL,
			"softirq": NO_DATA_SENTINEL,
			"iowait": NO_DATA_SENTINEL,
		}
		max_mode = max(mode_cpus, key=lambda k: mode_cpus[k])
		max_cpu = mode_cpus[max_mode]
		return max_mode, max_cpu

	def _is_resource_overloaded(
		self, resource_type: Literal["Server", "Database Server"], resource: str
	) -> bool:
		"""Return True if the given resource is unreachable or has a high load avg."""
		load = self.incident.server_load15 if resource_type == "Server" else self.incident.db_server_load15
		if load == NO_DATA_SENTINEL:
			return True  # if no data, assume the resource is overloaded

		vm_name = str(frappe.db.get_value(resource_type, resource, "virtual_machine"))
		vcpu = int(frappe.db.get_value("Virtual Machine", vm_name, "vcpu") or 16)
		return load > HIGH_LOAD_FACTOR * vcpu

	# endregion

	# region Grafana screenshots

	@filelock("grafana_screenshots")  # prevent 100 chromes from opening
	def capture_grafana_dashboards(self, save: bool = True):
		if not frappe.db.get_single_value("Incident Settings", "grafana_screenshots"):
			return

		if not self.monitor_server.node_exporter_dashboard_path:
			frappe.log_error("Node Exporter dashboard path not set on Monitor Server")
			return

		with sync_playwright() as p:
			browser = p.chromium.launch(headless=True, channel="chromium")
			page = browser.new_page(locale="en-IN", timezone_id="Asia/Kolkata")
			page.set_extra_http_headers({"Authorization": self.monitor_server.get_grafana_auth_header()})

			self._capture_node_exporter_dashboard(page, "Server")
			self._capture_node_exporter_dashboard(page, "Database Server")

			browser.close()

		if save:
			self.incident.save()

	def _capture_node_exporter_dashboard(
		self, page: Page, server_type: Literal["Server", "Database Server"]
	) -> str | None:
		instance = self.incident.server if server_type == "Server" else self.incident.database_server
		if not instance:
			return None

		# Set fixed viewport before navigation for consistency
		page.set_viewport_size({"width": 1280, "height": 900})

		page.goto(
			f"https://{self.monitor_server.name}{self.monitor_server.node_exporter_dashboard_path}"
			f"&refresh=5m&var-DS_PROMETHEUS=Prometheus&var-job=node&var-node={instance}"
			"&from=now-1h&to=now"
			"&theme=light"
		)
		page.wait_for_load_state("networkidle")

		# wait 2 more seconds to settle animations
		page.wait_for_timeout(2000)

		# capture scrollbar-view area
		image_bytes = page.locator("#pageContent").screenshot()

		file = save_file(
			fname=f"{self.incident.name}_{server_type.lower().replace(' ', '_')}.png",
			content=image_bytes,
			dt=self.incident.doctype,
			dn=self.incident.name,
			is_private=1,
		)

		if server_type == "Server":
			self.incident.app_server_stats = file.file_url
		else:
			self.incident.db_server_stats = file.file_url

	# endregion


def check_tls_issue_bulk(domains: list[str]) -> dict[str, bool]:
	"""
	Returns:
		{hostname: tls_failed_bool}

		True  -> TLS failed
		False -> TLS OK
	"""
	import socket
	import ssl
	from concurrent.futures import ThreadPoolExecutor, as_completed

	def _check(hostname):
		context = ssl.create_default_context()
		try:
			with (
				socket.create_connection((hostname, 443), timeout=5) as sock,
				context.wrap_socket(sock, server_hostname=hostname),
			):
				return False
		except Exception:
			return True

	results: dict[str, bool] = {}

	if not domains:
		return results

	with ThreadPoolExecutor(max_workers=10) as executor:
		future_to_host = {executor.submit(_check, h): h for h in domains}

		for future in as_completed(future_to_host):
			host = future_to_host[future]
			try:
				results[host] = future.result()
			except Exception:
				results[host] = True  # fail-safe

	return results
