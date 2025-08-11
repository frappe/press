# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import random
import typing

import frappe
import requests
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from prometheus_api_client import MetricRangeDataFrame, PrometheusConnect
from prometheus_api_client.utils import parse_datetime

if typing.TYPE_CHECKING:
	from collections.abc import Callable


INVESTIGATION_WINDOW = "5m"  # Use 5m timeframe


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

		from press.incident_management.doctype.investigation_steps.investigation_steps import (
			InvestigationSteps,
		)

		database_investigation_steps: DF.Table[InvestigationSteps]
		incident: DF.Link | None
		proxy_investigation_steps: DF.Table[InvestigationSteps]
		server: DF.Link | None
		server_investigation_steps: DF.Table[InvestigationSteps]
	# end: auto-generated types

	@property
	def prometheus_client(self) -> PrometheusConnect:
		return get_prometheus_client()

	def unable_to_investigate(self, step: str, reasoning: str): ...

	def has_high_system_load(self, instance: str, threshold: float) -> bool:
		"""Check number of processes waiting for cpu time
		if the number is higher than 3 times the number of vcpus load is high
		"""
		start_time = parse_datetime(INVESTIGATION_WINDOW)
		end_time = parse_datetime("now")

		metric_data = self.prometheus_client.get_metric_range_data(
			metric_name="node_load5",
			label_config={"instance": instance, "job": "node"},
			start_time=start_time,
			end_time=end_time,
			chunk_size=(end_time - start_time),
		)

		if not metric_data:
			self.unable_to_investigate(
				"System Load", f"Unable to get node exporter values for instance {instance}"
			)

		metric_data = MetricRangeDataFrame(metric_data)
		return metric_data.value.mean() > threshold

	def has_high_cpu_load(self, instance: str, threshold: float) -> bool:
		"""Check high cpu load"""
		query = f"""
				100 - (avg by (instance) (
					rate(node_cpu_seconds_total{{instance="{instance}",mode="idle"}}[{INVESTIGATION_WINDOW}])
				) * 100)
				"""

		metric_data = self.prometheus_client.get_current_metric_value(query)
		if not metric_data:
			self.unable_to_investigate(
				"CPU Usage", f"Unable to get node exporter values for instance {instance}"
			)

		return metric_data[0]["value"][-1] > threshold

	def has_high_memory_usage(self, instance: str, threshold: float) -> bool:
		"Determine high memory usage"
		query = f"""
				(
					1 - (
						node_memory_MemAvailable_bytes{{instance="{instance}"}}
						/
						node_memory_MemTotal_bytes{{instance="{instance}"}}
					)
				) * 100
				"""

		metric_data = self.prometheus_client.get_current_metric_value(query)

		if not metric_data:
			self.unable_to_investigate(
				"Memory Usage", f"Unable to get node exporter values for instance {instance}"
			)

		return metric_data[0]["value"][-1] > threshold

	def has_high_disk_usage(self, instance: str, threshold: float) -> dict[str, bool]:
		"""Determined if disk is full in any of the relevant mountpoints"""
		mountpoints = {"/": False, "/opt/volumes/benches": False, "/opt/volumes/mariadb": False}

		for mountpoint in mountpoints:
			query = (
				f"""node_filesystem_avail_bytes{{instance="{instance}", job="node", mountpoint="{mountpoint}"}}""",
			)
			metric_data = self.prometheus_client.get_current_metric_value(query)
			if metric_data:
				free_space = float(metric_data[0]["value"][-1]) / 1024**3
				mountpoints[mountpoint] = free_space < threshold

		return mountpoint

	def are_sites_down_proxy(self, instance: str) -> bool:
		"""Randomly sample and ping 10% of sites on proxy"""

		def ping(url: str) -> int:
			return requests.get(url).status_code

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
		sampled_sites = random.sample(sites, sample_size)
		ping_results = [ping(site) for site in sampled_sites]

		return all(status != 200 for status in ping_results)

	@property
	def steps(self) -> dict[str, list[tuple[str, "Callable"]]]:
		investigation_steps = [
			(self.has_high_disk_usage.__doc__, self.has_high_disk_usage),
			(self.has_high_memory_usage.__doc__, self.has_high_memory_usage),
			(self.has_high_cpu_load.__doc__, self.has_high_cpu_load),
			(self.has_high_system_load.__doc__, self.has_high_system_load),
		]
		return {
			"proxy_investigation_steps": [
				(self.are_sites_down_proxy.__doc__, self.are_sites_down_proxy),
				*investigation_steps[1:],
			],  # Don't care about disk usage in proxy's case
			"server_investigation_steps": investigation_steps,
			"database_investigation_steps": investigation_steps,
		}

	def add_investigation_steps(self):
		"""Add Investigation steps for [f/m/n] server"""
		for steps_for, steps in self.steps.items():
			for step in steps:
				self.append(
					steps_for,
					{"step_name": step[0], "reasoning": "", "is_likely_cause": False},
				)
				self.save()

	def after_insert(self):
		self.add_investigation_steps()

	def investigate_proxy_server(self): ...

	def investigate_database_server(self): ...

	def investigate_server(self): ...

	def investigate(self):
		"""
		Rules for investigation
		CPU Utilization - Is the server overworked?
		Memory Usage - Is the server running out of RAM?
		Disk Usage - Is storage full?
		System Load - Are processes queuing up?
		"""
		...
