# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import datetime
import json
import random
import typing
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum

import frappe
import requests
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from prometheus_api_client import MetricRangeDataFrame, PrometheusConnect
from prometheus_api_client.utils import parse_datetime

from press.runner import Ansible, StepHandler
from press.runner import Status as StepStatus

if typing.TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine
	from press.press.incident_management.doctype.action_step.action_step import ActionStep
	from press.press.incident_management.doctype.investigation_step.investigation_step import (
		InvestigationStep,
	)


INVESTIGATION_WINDOW = "5m"  # Use 5m timeframe


class Status(str, Enum):
	PENDING = "Pending"
	INVESTIGATING = "Investigating"
	COMPLETED = "Completed"


def get_prometheus_client() -> PrometheusConnect:
	"""Get prometheus client"""
	monitor_server = frappe.db.get_single_value("Press Settings", "monitor_server") or "monitor.frappe.cloud"
	password = (
		get_decrypted_password("Monitor Server", monitor_server, "grafana_password", raise_exception=False)
		or "e7c16a69c8319ce5363014ad841d9f78"
	)
	return PrometheusConnect(f"https://{monitor_server}/prometheus", auth=("frappe", password))


@dataclass
class PrometheusInvestigationHelper:
	high_system_load_threshold: int
	high_cpu_load_threshold: int
	high_memory_usage_threshold: int
	high_disk_usage_threshold_in_gb: int
	prometheus_client: PrometheusConnect = field(default_factory=get_prometheus_client)
	investigation_window_start_time: datetime.datetime = field(
		default_factory=lambda: parse_datetime(INVESTIGATION_WINDOW)
	)
	investigation_window_end_time: datetime.datetime = field(default_factory=lambda: parse_datetime("now"))

	# Define the investigation steps for different servers
	INVESTIGATION_CHECKS: typing.ClassVar = {
		"server_investigation_steps": [
			"has_high_disk_usage",
			"has_high_cpu_load",
			"has_high_memory_usage",
			"has_high_system_load",
		],
		"database_investigation_steps": [
			"has_high_disk_usage",
			"has_high_cpu_load",
			"has_high_memory_usage",
			"has_high_system_load",
		],
		"proxy_investigation_steps": ["are_sites_on_proxy_down"],
	}

	@classmethod
	def load_from_server(
		cls,
		server: str,
		high_cpu_load_threshold,
		high_memory_usage_threshold,
		high_disk_usage_threshold_in_gb,
	) -> "PrometheusInvestigationHelper":
		"""Initialize PrometheusInvestigationHelper with server-specific thresholds"""
		return cls(
			high_cpu_load_threshold=high_cpu_load_threshold,
			high_memory_usage_threshold=high_memory_usage_threshold,
			high_disk_usage_threshold_in_gb=high_disk_usage_threshold_in_gb,
			high_system_load_threshold=3 * frappe.db.get_value("Virtual Machine", server, "vcpu")
			or 4,  # Placeholder, will be set based on vcpus
		)

	def is_unable_to_investigate(self, step: "InvestigationStep"):
		step.is_unable_to_investigate = True
		step.save()

	def has_high_system_load(self, instance: str, step: "InvestigationStep"):
		"""Check number of processes waiting for cpu time
		if the number is higher than 3 times the number of vcpus load is high
		"""
		assert self.investigation_window_start_time and self.investigation_window_end_time, (
			"Investigation window not set"
		)
		metric_data = self.prometheus_client.get_metric_range_data(
			metric_name="node_load5",
			label_config={"instance": instance, "job": "node"},
			start_time=self.investigation_window_start_time,
			end_time=self.investigation_window_end_time,
			chunk_size=(self.investigation_window_end_time - self.investigation_window_start_time),
		)

		if not metric_data:
			self.is_unable_to_investigate(step)
			return None

		metric_data = MetricRangeDataFrame(metric_data, ts_as_datetime=False)
		step.is_likely_cause = float(metric_data.value.mean()) > self.high_system_load_threshold
		step.save()

		return metric_data.to_dict()

	def has_high_cpu_load(self, instance: str, step: "InvestigationStep"):
		"""Check high cpu rate during window"""
		query = f'node_cpu_seconds_total{{instance="{instance}",mode="idle"}}'
		assert self.investigation_window_start_time and self.investigation_window_end_time, (
			"Investigation window not set"
		)

		metric_data = self.prometheus_client.custom_query_range(
			query,
			start_time=self.investigation_window_start_time,
			end_time=self.investigation_window_end_time,
			step="1m",
		)

		if not metric_data or len(metric_data[0]["values"]) < 2:
			self.is_unable_to_investigate(step)
			return None

		values = metric_data[0]["values"]
		cpu_idle_rate = (float(values[-1][1]) - float(values[0][1])) / (
			self.investigation_window_end_time - self.investigation_window_start_time
		).total_seconds()
		cpu_busy_percentage = (1 - cpu_idle_rate) * 100

		step.is_likely_cause = cpu_busy_percentage > self.high_cpu_load_threshold
		step.save()

		return metric_data.to_dict()

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
			return None

		metric_data = MetricRangeDataFrame(metric_data, ts_as_datetime=False)
		step.is_likely_cause = float(metric_data.value.mean()) > self.high_memory_usage_threshold
		step.save()

		return metric_data.to_dict()

	def has_high_disk_usage(self, instance: str, step: "InvestigationStep"):
		"""Determined if disk is full in any of the relevant mountpoints at present"""
		is_unreachable = True
		mountpoints = {"/": False, "/opt/volumes/benches": False, "/opt/volumes/mariadb": False}

		for mountpoint in mountpoints:
			query = f"""node_filesystem_avail_bytes{{instance="{instance}", job="node", mountpoint="{mountpoint}"}}"""
			metric_data = self.prometheus_client.get_current_metric_value(query)
			if metric_data:
				is_unreachable = False  # We need to get metric from at least one mountpoint
				free_space = float(metric_data[0]["value"][-1]) / 1024**3
				mountpoints[mountpoint] = free_space < self.high_disk_usage_threshold_in_gb

		if is_unreachable:
			self.is_unable_to_investigate(step)
			return None

		step.is_likely_cause = any(mountpoints.values())
		step.save()

		return mountpoints

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


class DatabaseInvestigationActions:
	def __init__(
		self,
		investigator: "IncidentInvestigator",
	):
		self.investigator = investigator

	def capture_process_list(self, step: "ActionStep"):
		"""Try to capture process list on database server"""
		step.status = StepStatus.Running
		step.save()

		database_server = frappe.db.get_value("Server", self.investigator.server, "database_server")
		database_server_doc: DatabaseServer = frappe.get_cached_doc("Database Server", database_server)

		try:
			ansible = Ansible(
				playbook="capture_process_list.yml",
				server=database_server_doc,
				user=database_server_doc._ssh_user(),
				port=database_server_doc._ssh_port(),
				variables={"timeout": 10},  # Try this for 10 seconds
			)
			self.investigator.handle_ansible_play(step, ansible)
		except Exception as e:
			self.investigator._fail_ansible_step(step, ansible, e)
			# Don't raise here since it might fail due to timeout or CPU freeze

	def initiate_database_reboot(self, step: "ActionStep"):
		"""Reboot database server in case of unreachable/missing metrics"""
		step.status = StepStatus.Running
		step.save()

		database_server = frappe.db.get_value("Server", self.investigator.server, "database_server")
		virtual_machine = frappe.db.get_value("Database Server", database_server, "virtual_machine")
		provider = frappe.db.get_value("Virtual Machine", virtual_machine, "cloud_provider")

		virtual_machine_doc: VirtualMachine = frappe.get_cached_doc("Virtual Machine", virtual_machine)
		if provider == "AWS EC2":
			virtual_machine_doc.reboot_with_serial_console()
		else:
			virtual_machine_doc.reboot()

		step.status = StepStatus.Success
		step.save()

	def add_database_server_investigation_actions(self):
		"""
		In case of database resource incidents we do the following
			- Unreachable or missing metrics from promethues results in a database server reboot
			- Busy resources result in a mariadb reboot post a process list capture.
		"""
		if any(
			[step for step in self.investigator.database_investigation_steps if step.is_unable_to_investigate]
		):
			# We need to think about missing data from prometheus here?
			for step in self.investigator.get_steps([self.initiate_database_reboot]):
				self.investigator.append("action_steps", step)

			self.investigator.save()
			return

		database_likely_causes = set(self.investigator.likely_causes["database"])
		if (
			database_likely_causes
			and database_likely_causes.issubset(
				{
					PrometheusInvestigationHelper.has_high_cpu_load.__name__,
					PrometheusInvestigationHelper.has_high_memory_usage.__name__,
					PrometheusInvestigationHelper.has_high_system_load.__name__,
				}
			)
			and database_likely_causes
			!= {
				PrometheusInvestigationHelper.has_high_memory_usage.__name__
			}  # This ensure that memory high is not the only likely cause
		):  # don't trigger this only for high memory issues
			for step in self.investigator.get_steps(
				[self.capture_process_list, self.initiate_database_reboot]
			):
				self.investigator.append("action_steps", step)

		self.investigator.save()


class IncidentInvestigator(Document, StepHandler):
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

	def set_status(self, status: str):
		"Set/Update investigation status"
		self.status = status
		self.save()

	def add_investigation_findings(self, step: str, data: Mapping[str, int | str | bool] | list):
		"""Add investigation findings from each step"""
		findings = json.loads(self.investigation_findings) if self.investigation_findings else {}
		findings[step] = data
		self.investigation_findings = json.dumps(findings, indent=2)
		self.save()

	### Some helper methods for initiating investigation steps
	@property
	def likely_causes(self):
		"""Return likely causes for database and server from investigation"""
		return {
			"database": [step.method for step in self.database_investigation_steps if step.is_likely_cause],
			"server": [step.method for step in self.database_investigation_steps if step.is_likely_cause],
			"proxy": [step.method for step in self.proxy_investigation_steps if step.is_likely_cause],
		}

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

	def add_investigation_steps(self):
		"""Add Investigation steps for [f/m/n] server"""
		for step_key, methods in PrometheusInvestigationHelper.INVESTIGATION_CHECKS.items():
			for method in methods:
				step_name = getattr(PrometheusInvestigationHelper, method).__doc__
				self.append(
					step_key,
					{
						"step_name": step_name,
						"method": method,
						"is_likely_cause": False,
						"is_unable_to_investigate": False,
					},
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

		self.add_investigation_steps()
		self.action_steps = []

	def after_insert(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"investigate",
			queue="long",
			enqueue_after_commit=True,
		)

	def investigate(self):
		"""Main method to execute investigation steps in order"""
		self.set_status(Status.INVESTIGATING)
		self.prometheus_investigation_helper = PrometheusInvestigationHelper.load_from_server(
			self.server,
			self.high_cpu_load_threshold,
			self.high_memory_usage_threshold,
			self.high_disk_usage_threshold_in_gb,
		)

		for step_key, methods in PrometheusInvestigationHelper.INVESTIGATION_CHECKS.items():
			for method in methods:
				investigation_method = getattr(self.prometheus_investigation_helper, method)
				if step_key == "server_investigation_steps":
					investigation_method(
						instance=self.server,
						step=find(self.server_investigation_steps, lambda s: s.method == method),
					)
				elif step_key == "database_investigation_steps":
					database_server = frappe.db.get_value("Server", self.server, "database_server")
					investigation_method(
						instance=database_server,
						step=find(self.database_investigation_steps, lambda s: s.method == method),
					)
				elif step_key == "proxy_investigation_steps":
					proxy_server = frappe.db.get_value("Server", self.server, "proxy_server")
					investigation_method(
						instance=proxy_server,
						step=find(self.proxy_investigation_steps, lambda s: s.method == method),
					)

		self.post_investigation()

	def post_investigation(self):
		"""Perform post-investigation actions"""
		database_investigation_actions = DatabaseInvestigationActions(self)
		database_investigation_actions.add_database_server_investigation_actions()

		execute_action_steps = frappe.db.get_single_value(
			"Press Settings", "execute_incident_action", cache=True
		)

		if self.action_steps and execute_action_steps:
			# Execute action steps via step handler
			frappe.enqueue_doc(
				self.doctype,
				self.name,
				"_execute_steps",
				method_classes=[database_investigation_actions],
				start_status=Status.INVESTIGATING,
				success_status=Status.COMPLETED,
				failure_status=Status.COMPLETED,  # We mark any failed step also as completed investigation
				steps=self.action_steps,
				queue="long",
				at_front=True,
				enqueue_after_commit=True,
			)

		if not execute_action_steps or not self.action_steps:
			self.set_status(Status.COMPLETED)

	@frappe.whitelist()
	def start_investigation(self):
		if self.status == "Pending":
			self.action_steps = []
			self.save()
			frappe.enqueue_doc(self.doctype, self.name, "investigate", queue="long")
