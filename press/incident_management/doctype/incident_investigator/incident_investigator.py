# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import json
import random
import time
import typing
from enum import Enum

import frappe
import requests
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from prometheus_api_client import MetricRangeDataFrame, PrometheusConnect
from prometheus_api_client.utils import parse_datetime

if typing.TYPE_CHECKING:
	import datetime
	from collections.abc import Callable

	from press.press.incident_management.doctype.action_step.action_step import (
		ActionStep,
	)
	from press.press.incident_management.doctype.investigation_step.investigation_step import (
		InvestigationStep,
	)


INVESTIGATION_WINDOW = "5m"  # Use 5m timeframe


class Status(Enum):
	PENDING = "Pending"
	INVESTIGATING = "Investigating"
	COMPLETED = "Completed"


def get_prometheus_client() -> PrometheusConnect:
	"""Get prometheus client"""
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server")
	password = get_decrypted_password("Monitor Server", monitor_server, "grafana_password")
	return PrometheusConnect(f"https://{monitor_server}/prometheus", auth=("frappe", password))


class IncidentInvestigator(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.incident_management.doctype.action_step.action_step import ActionStep
		from press.incident_management.doctype.investigation_step.investigation_step import InvestigationStep

		action_steps: DF.Table[ActionStep]
		cool_off_period: DF.Float
		database_investigation_steps: DF.Table[InvestigationStep]
		high_cpu_load_threshold: DF.Int
		high_disk_usage_threshold_in_gb: DF.Int
		high_memory_usage_threshold: DF.Int
		high_system_load_threshold: DF.Int
		incident: DF.Link | None
		investigation_findings: DF.JSON | None
		investigation_window_end_time: DF.Datetime | None
		investigation_window_start_time: DF.Datetime | None
		proxy_investigation_steps: DF.Table[InvestigationStep]
		server: DF.Link | None
		server_investigation_steps: DF.Table[InvestigationStep]
		status: DF.Literal["Pending", "Investigating", "Completed"]
	# end: auto-generated types

	@property
	def prometheus_client(self) -> PrometheusConnect:
		return get_prometheus_client()

	def is_unable_to_investigate(self, step: "InvestigationStep"):
		step.is_unable_to_investigate = True
		step.save()

	def add_investigation_findings(self, step: str, data: dict[str : int | str] | list):
		"""Add investigation findings from each step"""
		findings = json.loads(self.investigation_findings) if self.investigation_findings else {}
		findings[step] = data
		self.investigation_findings = json.dumps(findings, indent=2)
		self.save()

	def has_high_system_load(self, instance: str, step: "InvestigationStep"):
		"""Check number of processes waiting for cpu time
		if the number is higher than 3 times the number of vcpus load is high
		"""
		metric_data = self.prometheus_client.get_metric_range_data(
			metric_name="node_load5",
			label_config={"instance": instance, "job": "node"},
			start_time=self.investigation_window_start_time,
			end_time=self.investigation_window_end_time,
			chunk_size=(self.investigation_window_end_time - self.investigation_window_start_time),
		)

		if not metric_data:
			self.is_unable_to_investigate(step)
			return

		metric_data = MetricRangeDataFrame(metric_data, ts_as_datetime=False)
		step.is_likely_cause = float(metric_data.value.mean()) > self.high_system_load_threshold
		step.save()

		self.add_investigation_findings(f"{step.parentfield}-{step.step_name}", metric_data.to_dict())

	def has_high_cpu_load(self, instance: str, step: "InvestigationStep"):
		"""Check high cpu rate during window"""
		query = f'node_cpu_seconds_total{{instance="{instance}",mode="idle"}}'

		metric_data = self.prometheus_client.custom_query_range(
			query,
			start_time=self.investigation_window_start_time,
			end_time=self.investigation_window_end_time,
			step="1m",
		)

		if not metric_data or len(metric_data[0]["values"]) < 2:
			self.is_unable_to_investigate(step)
			return

		values = metric_data[0]["values"]
		cpu_idle_rate = (float(values[-1][1]) - float(values[0][1])) / (
			self.investigation_window_end_time - self.investigation_window_start_time
		).total_seconds()
		cpu_busy_percentage = (1 - cpu_idle_rate) * 100

		step.is_likely_cause = cpu_busy_percentage > self.high_cpu_load_threshold
		step.save()

		self.add_investigation_findings(f"{step.parentfield}-{step.step_name}", metric_data)

	def has_high_memory_usage(self, instance: str, step: "InvestigationStep"):
		"Determine high memory usage over a period of investigation window"
		query = f"""
				(
					1 - (
						node_memory_MemAvailable_bytes{{instance="{instance}"}}
						/
						node_memory_MemTotal_bytes{{instance="{instance}"}}
					)
				) * 100
				"""

		metric_data = self.prometheus_client.custom_query_range(
			query,
			start_time=self.investigation_window_start_time,
			end_time=self.investigation_window_end_time,
			step="1m",  # Since investigation window is of 5m resolution of 1m is fine for now
		)

		if not metric_data:
			self.is_unable_to_investigate(step)
			return

		metric_data = MetricRangeDataFrame(metric_data, ts_as_datetime=False)
		step.is_likely_cause = float(metric_data.value.mean()) > self.high_memory_usage_threshold
		step.save()

		self.add_investigation_findings(f"{step.parentfield}-{step.step_name}", metric_data.to_dict())

	def has_high_disk_usage(self, instance: str, step: "InvestigationStep"):
		"""Determined if disk is full in any of the relevant mountpoints at present"""
		is_unreachable = True
		mountpoints = {"/": False, "/opt/volumes/benches": False, "/opt/volumes/mariadb": False}

		for mountpoint in mountpoints:
			query = f"""node_filesystem_avail_bytes{{instance="{instance}", job="node", mountpoint="{mountpoint}"}}"""
			metric_data = self.prometheus_client.get_current_metric_value(query)
			if metric_data:
				is_unreachable = False  # We need to get metric from atleast one mountpoint
				free_space = float(metric_data[0]["value"][-1]) / 1024**3
				mountpoints[mountpoint] = free_space < self.high_disk_usage_threshold_in_gb

		if is_unreachable:
			self.is_unable_to_investigate(step)
			return

		step.is_likely_cause = any(mountpoints.values())
		step.save()

		self.add_investigation_findings(f"{step.parentfield}-{step.step_name}", mountpoints)

	def are_sites_on_proxy_down(self, instance: str, step: "InvestigationStep"):
		"""Randomly sample and ping 10% of sites on proxy"""

		def ping(url: str) -> int:
			try:
				return requests.get(f"https://{url}/api/method/ping", timeout=5).status_code
			except Exception:
				return 502

		Site = frappe.qb.DocType("Site")
		Server = frappe.qb.DocType("Server")

		sites = (
			frappe.qb.from_(Site)
			.select(Site.name)
			.join(Server)
			.on(Site.server == Server.name)
			.where(Server.proxy_server == instance)
			.where(Site.status == "Active")
			.run(pluck=True)
		)
		sample_size = max(1, int(len(sites) * 0.10))

		try:
			sampled_sites = random.sample(sites, sample_size)
		except ValueError:
			self.is_unable_to_investigate(step)
			return

		ping_results = [ping(site) for site in sampled_sites]

		step.is_likely_cause = all(status != 200 for status in ping_results)
		step.save()

		self.add_investigation_findings(f"{step.parentfield}-{step.step_name}", ping_results)

	@property
	def steps(self) -> dict[str, list[tuple[str, "Callable"]]]:
		investigation_steps = [
			(self.has_high_disk_usage.__doc__, self.has_high_disk_usage.__name__),
			(self.has_high_memory_usage.__doc__, self.has_high_memory_usage.__name__),
			(self.has_high_cpu_load.__doc__, self.has_high_cpu_load.__name__),
			(self.has_high_system_load.__doc__, self.has_high_system_load.__name__),
		]
		return {
			"proxy_investigation_steps": [
				(self.are_sites_on_proxy_down.__doc__, self.are_sites_on_proxy_down.__name__),
				# *investigation_steps[1:],
			],  # Don't care about disk usage in proxy's case
			"server_investigation_steps": investigation_steps,
			"database_investigation_steps": investigation_steps,
		}

	@property
	def likely_causes(self):
		"""Return likely causes for database and server from investigation"""
		return {
			"database": [step.method for step in self.database_investigation_steps if step.is_likely_cause],
			"server": [step.method for step in self.database_investigation_steps if step.is_likely_cause],
		}

	def add_investigation_steps(self):
		"""Add Investigation steps for [f/m/n] server"""
		for steps_for, steps in self.steps.items():
			for step in steps:
				self.append(
					steps_for,
					{
						"step_name": step[0],
						"method": step[1],
						"is_likely_cause": False,
						"is_unable_to_investigate": False,
					},
				)
				self.save()

	def set_prerequisites(self):
		"""Set investigation window and other thresholds"""
		self.investigation_window_start_time = parse_datetime(INVESTIGATION_WINDOW)
		self.investigation_window_end_time = parse_datetime("now")
		self.high_system_load_threshold = 3 * (
			frappe.db.get_value("Virtual Machine", self.server, "vcpu") or 4
		)
		self.set_status(Status.PENDING)
		self.save()

	def is_cluster_spam(self) -> bool:
		"""Check if another server in the same cluster has been effected"""
		Server = frappe.qb.DocType("Server")
		Investigator = frappe.qb.DocType("Incident Investigator")
		incident_cluster = frappe.db.get_value("Server", self.server, "cluster")

		# Getting the last reported incident on the cluster created in the last minute
		return bool(
			frappe.qb.from_(Investigator)
			.join(Server)
			.on(Server.name == Investigator.server)
			.select(Investigator.name)
			.where(Server.cluster == incident_cluster)
			.where(Investigator.creation[frappe.utils.add_to_date(minutes=-1) : frappe.utils.now()])
			.run(pluck=True)
		)

	def before_insert(self):
		"""
		Do not trigger investigation on the same server if cool off period has not passed
		Do not trigger investigation on self hosted servers
		Do not trigger investigation if same cluster spams
		"""
		if frappe.get_value("Server", self.server, "is_self_hosted"):
			frappe.throw(
				f"Ignoring investigation for self hosted server {self.server}", frappe.ValidationError
			)

		if self.is_cluster_spam():
			cluster = frappe.db.get_value("Server", self.server, "cluster")
			frappe.throw(
				f"Investigation for {cluster} is in a cool off period",
				frappe.ValidationError,
			)

		last_created_investigation = frappe.get_value(
			"Incident Investigator", {"server": self.server}, "creation"
		)

		if not last_created_investigation:
			return

		time_since_last_investigation: datetime.timedelta = parse_datetime("now") - last_created_investigation
		if time_since_last_investigation.total_seconds() < self.cool_off_period:
			frappe.throw(
				f"Investigation for {self.server} is in a cool off period",
				frappe.ValidationError,
			)

	def after_insert(self):
		self.set_prerequisites()
		self.add_investigation_steps()
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"investigate",
			queue="long",
			enqueue_after_commit=True,
		)

	@frappe.whitelist()
	def start_investigation(self):
		if self.status == "Pending":
			frappe.enqueue_doc(self.doctype, self.name, "investigate", queue="long")

	def set_status(self, status: Status):
		"Set/Update investigation status"
		self.status = status.value
		self.save(ignore_version=True)

	def _investigate_component(self, component_field: str, step_key: str):
		"""Generic investigation method for f/n/m servers."""
		component = frappe.db.get_value("Server", self.server, component_field)
		steps: list[InvestigationStep] = getattr(self, step_key)
		for step in steps:
			method = getattr(self, step.method)
			method(instance=component, step=step)

	def investigate_proxy_server(self):
		"""Investigate potential issues with the proxy server."""
		self._investigate_component("proxy_server", "proxy_investigation_steps")

	def investigate_database_server(self):
		"""Investigate potential issues with the database server."""
		self._investigate_component("database_server", "database_investigation_steps")

	def investigate_server(self):
		"""Investigate potential issues with the main application server."""
		self._investigate_component("name", "server_investigation_steps")

	def _check_process_list_capture(self) -> tuple[bool, bool]:
		"""Check if process list capture is completed first bool is for termination second is for status"""
		database_server = frappe.db.get_value("Server", self.server, "database_server")
		play_status = frappe.db.get_value(
			"Ansible Play",
			{
				"play": "Capture Process List",
				"server": database_server,
				"creation": (">", self.creation),
			},
			"status",
		)
		if not play_status:
			return False, False

		if play_status and play_status not in ("Success", "Failure"):
			return False, False

		# Terminated check status
		return True, play_status == "Success"

	def add_action(
		self,
		reference_doctype: str,
		reference_name: str,
		method: str,
		wait: bool = False,
	):
		"""Add action in the action steps"""
		action_step: ActionStep = self.append(
			"action_steps",
			{
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"method": method,
				"is_taken": False,
				"wait": wait,
			},
		)
		action_step.save()

	def _initiate_reboot_database(self, database_server: str):
		"""Trigger reboot depending on cloud provider"""
		# Explicitly getting the virtual machine in case of mismatches
		virtual_machine = frappe.db.get_value("Database Server", database_server, "virtual_machine")
		provider = frappe.db.get_value("Virtual Machine", virtual_machine, "cloud_provider")
		self.add_action(
			"Virtual Machine", virtual_machine, "reboot_with_serial_console"
		) if provider == "AWS EC2" else self.add_action("Virtual Machine", virtual_machine, "reboot")

	def _initiate_process_list_capture_and_reboot_mariadb(self, database_server: str):
		"""Capture database process list and restart mariadb"""
		self.add_action("Database Server", database_server, "capture_process_list")
		self.add_action("Incident Investigator", self.name, "_check_process_list_capture", wait=True)
		self.add_action("Database Server", database_server, "restart_mariadb")

	def add_proxy_investigation_actions(self):
		"""We currently do not add actions in case of proxy issues"""
		pass

	def add_server_investigation_actions(self):
		"""We currently do not add actions in case of application server issues"""
		pass

	def add_database_server_investigation_actions(self):
		"""
		In case of database resource incidents we do the following
			- Unreachable or missing metrics from promethues results in a database server reboot
			- Busy resources result in a mariadb reboot post a process list capture.
		"""
		database_server = frappe.db.get_value("Server", self.server, "database_server")

		if any([step for step in self.database_investigation_steps if step.is_unable_to_investigate]):
			self._initiate_reboot_database(database_server)
			return

		database_likely_causes = set(self.likely_causes["database"])
		if (
			database_likely_causes
			and database_likely_causes.issubset(
				{
					self.has_high_cpu_load.__name__,
					self.has_high_memory_usage.__name__,
					self.has_high_system_load.__name__,
				}
			)
			and database_likely_causes != {self.has_high_memory_usage.__name__}
		):  # don't trigger this only for high memory issues
			self._initiate_process_list_capture_and_reboot_mariadb(database_server)

	def add_investigation_actions(self):
		if self.add_proxy_investigation_actions():
			return

		self.add_server_investigation_actions()
		self.add_database_server_investigation_actions()

	def stop_calls_on_high_disk_usage(self):
		"""If the investigation shows high disk usage (only!) we can safely ignore calls"""
		if [self.has_high_disk_usage.__name__] == self.likely_causes["database"] or [
			self.has_high_disk_usage.__name__
		] == self.likely_causes["server"]:
			frappe.db.set_value("Incident", self.incident, "phone_call", False)

	def post_investigation(self):
		"""Stop calls in case of high disk usage & add investigation actions"""
		self.stop_calls_on_high_disk_usage()
		self.add_investigation_actions()
		execute_action_steps = frappe.db.get_single_value(
			"Press Settings", "execute_incident_action", cache=True
		)
		if self.action_steps and execute_action_steps:
			frappe.enqueue_doc(self.doctype, self.name, "execute_action_steps", queue="long")

	def execute_action_steps(self, max_retries: int = 60):
		"""
		Execute all action steps sequentially max retries of 60 with interval 5 (5 minutes)
		"""
		for step in self.action_steps:
			target_doc = frappe.get_doc(step.reference_doctype, step.reference_name)

			method = getattr(target_doc, step.method)
			if not step.wait:
				# Fire-and-forget execution
				method()
				self.add_comment(text=f"Called {step.method}")
				continue

			retries = 0
			while retries < max_retries:
				is_terminated, is_successful = method()

				if is_terminated and is_successful:
					# Step succeeded, continue to next step
					break
				if is_terminated and not is_successful:
					# Don't execute anything further
					return
				if not is_terminated:
					time.sleep(5)
					retries += 1
			else:
				frappe.throw(f"Step {step.method} did not terminate after {max_retries * 5} seconds")

	def investigate(self):
		"""
		Rules for investigation
		CPU Utilization - Is the server overworked?
		Memory Usage - Is the server running out of RAM?
		Disk Usage - Is storage full?
		System Load - Are processes queuing up?

		Proxy rules for investigation
		In addition to able we ping sites need to fast exit in case of likely cause
		"""
		self.set_status(Status.INVESTIGATING)
		self.investigate_proxy_server()
		self.investigate_database_server()
		self.investigate_server()
		self.set_status(Status.COMPLETED)

		self.post_investigation()
