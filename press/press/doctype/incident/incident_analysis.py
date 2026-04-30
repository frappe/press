# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from base64 import b64encode
from functools import cached_property
from typing import TYPE_CHECKING

import frappe
import requests
from frappe.utils.synchronization import filelock
from playwright.sync_api import Page, sync_playwright

from press.api.server import prometheus_query
from press.press.doctype.server.server import MARIADB_DATA_MNT_POINT

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.incident.incident import Incident
	from press.press.doctype.monitor_server.monitor_server import MonitorServer
	from press.press.doctype.press_settings.press_settings import PressSettings


# Heuristic thresholds used while categorising an incident.
HIGH_LOAD_FACTOR = 3  # load average > 3 * vCPU is considered high
CPU_BUSY_THRESHOLD_PERCENT = 70
NO_DATA_SENTINEL = -1


class IncidentAnalysis:
	"""Encapsulates resource identification, problem categorization and
	supporting evidence collection (Prometheus metrics, sample-site pings,
	Grafana screenshots) for an `Incident`.
	"""

	def __init__(self, incident: Incident):
		self.incident = incident

	@cached_property
	def monitor_server(self) -> MonitorServer:
		press_settings: PressSettings = frappe.get_cached_doc("Press Settings")
		if not (monitor_url := press_settings.monitor_server):
			frappe.throw("Monitor Server not set in Press Settings")
		return frappe.get_cached_doc("Monitor Server", monitor_url)

	def identify_affected_resource(self):
		"""Identify the affected resource and set it on the incident."""
		self.incident._add_description(
			f"{len(self.incident.sites_down)} / {self.incident.total_instances} sites down:"
		)
		self.incident._add_description("\n".join(self.incident.sites_down))

		candidates = [
			("Database Server", self.incident.database_server),
			("Server", self.incident.server),
		]
		for resource_type, resource in candidates:
			if self._is_resource_overloaded(resource_type, resource):
				self.incident.resource_type = resource_type
				self.incident.resource = resource
				return

	def categorize_problem(self):
		if self._try_categorize_as_disk_full():
			return

		# TODO: Try more if resource isn't identified.
		# Eg: Check mysql up/ docker up/ container up. Use site error code:
		# 500 = mysql down or app/config bug, 502 = server/bench down,
		# 504 = overloaded workers.

		state, percent = self.measure_dominant_cpu_mode(self.incident.resource)
		if state == "idle" or percent < CPU_BUSY_THRESHOLD_PERCENT:
			return

		if self.incident.resource_type == "Database Server":
			self.incident.type = "Database Down"
		elif self.incident.resource_type == "Server":
			self.incident.type = "Server Down"
		# TODO: categorize proxy issues #

		if state == "user":
			self.incident.subtype = "High CPU: user"
		elif state == "iowait":
			self.incident.subtype = "High CPU: iowait"

		self.incident.save()

	# ------------------------------------------------------------------
	# Resource identification helpers
	# ------------------------------------------------------------------

	def _is_resource_overloaded(self, resource_type: str, resource: str) -> bool:
		"""Return True if the given resource is unreachable or has a high load avg."""
		load = self.measure_load_avg(resource)
		if load < 0:  # no response, likely down
			return True

		vm_name = str(frappe.db.get_value(resource_type, resource, "virtual_machine"))
		vcpu = int(frappe.db.get_value("Virtual Machine", vm_name, "vcpu") or 16)
		return load > HIGH_LOAD_FACTOR * vcpu

	# ------------------------------------------------------------------
	# Categorization
	# ------------------------------------------------------------------

	def _try_categorize_as_disk_full(self) -> bool:
		"""If the sample site returns 500 and the DB disk is full, mark the incident."""
		incident = self.incident
		pong = self.ping_sample_site()
		if incident.resource or pong != 500:
			return False

		db: DatabaseServer = frappe.get_doc("Database Server", incident.database_server)
		if not db.is_disk_full(MARIADB_DATA_MNT_POINT):
			return False

		incident.resource_type = "Database Server"
		incident.resource = incident.database_server
		incident.type = "Database Down"
		incident.subtype = "Disk full"
		incident.likely_cause = "Disk is full"
		incident.communication.send_disk_full_mail()
		return True

	# ------------------------------------------------------------------
	# Prometheus probes
	# ------------------------------------------------------------------

	def measure_load_avg(self, name) -> float:
		"""Return 5-minute load average for the given instance, recording it as a finding."""
		timespan = self.incident.settings.confirmation_threshold_seconds
		load = prometheus_query(
			f"""avg_over_time(node_load5{{instance="{name}", job="node"}}[{timespan}s])""",
			lambda x: x,
			"Asia/Kolkata",
			timespan,
			timespan + 1,
		)["datasets"]
		value = load[0]["values"][-1] if load else NO_DATA_SENTINEL
		if value != NO_DATA_SENTINEL:
			self.incident._add_finding(f"{name} load avg (5m)", value)
		return value

	def measure_dominant_cpu_mode(self, resource: str) -> tuple[str, float]:
		"""Return the dominant CPU mode and its percentage for the given instance."""
		timespan = self.incident.settings.confirmation_threshold_seconds
		cpu_info = prometheus_query(
			f"""avg by (mode)(rate(node_cpu_seconds_total{{instance="{resource}", job="node"}}[{timespan}s])) * 100""",
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
		if max_cpu > 0:
			self.incident._add_finding(f"{resource} CPU ({max_mode})", f"{max_cpu:.2f}%")
		return max_mode, max_cpu

	def ping_sample_site(self):
		site = self.incident.get_down_site()
		if not site:
			return None
		try:
			ret = requests.get(f"https://{site}/api/method/ping", timeout=10)
		except requests.RequestException as e:
			self.incident._add_finding(f"Ping {site}", f"Error: {e!s}")
			return None

		self.incident._add_finding(f"Ping {site}", f"{ret.status_code} {ret.reason}")
		return ret.status_code

	# ------------------------------------------------------------------
	# Grafana screenshots
	# ------------------------------------------------------------------

	@filelock("grafana_screenshots")  # prevent 100 chromes from opening
	def capture_grafana_dashboards(self):
		if not frappe.db.get_single_value("Incident Settings", "grafana_screenshots"):
			return

		with sync_playwright() as p:
			browser = p.chromium.launch(headless=True, channel="chromium")
			page = browser.new_page(locale="en-IN", timezone_id="Asia/Kolkata")
			page.set_extra_http_headers({"Authorization": self.monitor_server.get_grafana_auth_header()})

			self._capture_node_exporter_dashboard(page, self.incident.resource or self.incident.server)
			self._capture_node_exporter_dashboard(page, self._paired_resource())

		self.incident.save()

	def _capture_node_exporter_dashboard(self, page: Page, instance: str | None):
		if not instance:
			return

		page.goto(
			f"https://{self.monitor_server.name}{self.monitor_server.node_exporter_dashboard_path}"
			f"&refresh=5m&var-DS_PROMETHEUS=Prometheus&var-job=node&var-node={instance}"
			"&from=now-1h&to=now"
		)
		page.wait_for_load_state("networkidle")

		image = b64encode(page.screenshot()).decode("ascii")
		self.incident._add_description(f'<img src="data:image/png;base64,{image}" alt="grafana-image">')

	def _paired_resource(self) -> str | None:
		incident = self.incident
		if incident.resource_type == "Database Server":
			return str(incident.server)
		if incident.resource_type == "Server":
			return str(frappe.db.get_value("Server", incident.resource, "database_server"))
		return None
