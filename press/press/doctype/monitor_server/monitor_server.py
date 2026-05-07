# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import contextlib
import json
from base64 import b64encode
from urllib.parse import urljoin

import frappe
import requests
from frappe.utils.caching import redis_cache
from frappe.utils.data import cint
from prometheus_api_client import PrometheusConnect
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_exponential

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class _BaseUrlSession(requests.Session):
	"""`requests.Session` that prepends a base URL to relative routes."""

	def __init__(self, base_url: str):
		super().__init__()
		self.base_url = base_url.rstrip("/") + "/"

	def request(self, method, url, *args, **kwargs):
		return super().request(method, urljoin(self.base_url, url.lstrip("/")), *args, **kwargs)


class MonitorServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_password: DF.Password | None
		cluster: DF.Link | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		grafana_password: DF.Password | None
		grafana_username: DF.Data | None
		hostname: DF.Data
		ip: DF.Data | None
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		node_exporter_dashboard_path: DF.Data | None
		only_monitor_uptime_metrics: DF.Check
		plan: DF.Link | None
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		prometheus_data_directory: DF.Data | None
		prometheus_username: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tls_certificate_renewal_failed: DF.Check
		virtual_machine: DF.Link | None
		webhook_token: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_agent_password()
		self.validate_grafana_password()
		self.validate_monitoring_password()
		self.validate_webhook_token()

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def validate_grafana_password(self):
		if not self.grafana_password:
			self.grafana_password = frappe.generate_hash(length=32)

	def validate_webhook_token(self):
		if not self.webhook_token:
			self.webhook_token = frappe.generate_hash(length=32)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		monitoring_password = self.get_password("monitoring_password")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)

		registries = []
		for registry in frappe.get_all("Registry Server"):
			registry = frappe.get_doc("Registry Server", registry.name)
			registries.append(
				{
					"name": registry.name,
					"monitoring_password": registry.get_password("monitoring_password"),
				}
			)

		log_servers = []
		for log in frappe.get_all("Log Server"):
			log = frappe.get_doc("Log Server", log.name)
			log_servers.append(
				{
					"name": log.name,
					"monitoring_password": log.get_password("monitoring_password"),
				}
			)

		clusters = []
		for cluster in frappe.get_all("Cluster"):
			cluster = frappe.get_doc("Cluster", cluster.name)
			clusters.append(
				{
					"name": cluster.name,
					"monitoring_password": cluster.get_password("monitoring_password"),
				}
			)
		press_url = frappe.utils.get_url()
		settings = frappe.get_single("Press Settings")
		monitor_token = settings.monitor_token
		press_monitoring_password = settings.get_password("press_monitoring_password")
		try:
			ansible = Ansible(
				playbook="monitor.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"monitor": True,
					"monitoring_password": monitoring_password,
					"press_monitoring_password": press_monitoring_password,
					"press_app_server": frappe.local.site,
					"press_db_server": f"db.{frappe.local.site}",
					"press_db_replica_server": f"db2.{frappe.local.site}" if frappe.conf.replica_host else "",
					"press_url": press_url,
					"prometheus_data_directory": self.prometheus_data_directory,
					"monitor_token": monitor_token,
					"registries_json": json.dumps(registries),
					"log_servers_json": json.dumps(log_servers),
					"clusters_json": json.dumps(clusters),
					"private_ip": self.private_ip,
					"grafana_password": self.get_password("grafana_password"),
					"certificate_private_key": certificate.private_key,
					"certificate_full_chain": certificate.full_chain,
					"certificate_intermediate_chain": certificate.intermediate_chain,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Monitor Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def reconfigure_monitor_server(self):
		frappe.enqueue_doc(self.doctype, self.name, "_reconfigure_monitor_server", queue="long", timeout=1200)

	def _reconfigure_monitor_server(self):
		settings = frappe.get_single("Press Settings")
		press_monitoring_password = settings.get_password("press_monitoring_password")
		monitoring_password = self.get_password("monitoring_password")

		registries = []
		for registry in frappe.get_all("Registry Server"):
			registry = frappe.get_doc("Registry Server", registry.name)
			registries.append(
				{
					"name": registry.name,
					"monitoring_password": registry.get_password("monitoring_password"),
				}
			)

		log_servers = []
		for log in frappe.get_all("Log Server"):
			log = frappe.get_doc("Log Server", log.name)
			log_servers.append(
				{
					"name": log.name,
					"monitoring_password": log.get_password("monitoring_password"),
				}
			)

		clusters = []
		for cluster in frappe.get_all("Cluster"):
			cluster = frappe.get_doc("Cluster", cluster.name)
			clusters.append(
				{
					"name": cluster.name,
					"monitoring_password": cluster.get_password("monitoring_password"),
				}
			)

		try:
			ansible = Ansible(
				playbook="reconfigure_monitoring.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"monitoring_password": monitoring_password,
					"press_monitoring_password": press_monitoring_password,
					"press_app_server": frappe.local.site,
					"press_db_server": f"db.{frappe.local.site}",
					"press_db_replica_server": f"db2.{frappe.local.site}" if frappe.conf.replica_host else "",
					"registries_json": json.dumps(registries),
					"log_servers_json": json.dumps(log_servers),
					"clusters_json": json.dumps(clusters),
					"grafana_password": self.get_password("grafana_password"),
				},
			)
			ansible.run()
		except Exception:
			log_error("Monitoring Server Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def update_alert_rules(self):
		from press.press.doctype.prometheus_alert_rule.prometheus_alert_rule import PrometheusAlertRule

		PrometheusAlertRule.update_alert_rules_on_monitor(self.name)

	@frappe.whitelist()
	def show_grafana_password(self):
		return self.get_password("grafana_password")

	def get_grafana_auth_header(self):
		username = str(self.grafana_username)
		password = str(self.get_password("grafana_password"))
		token = b64encode(f"{username}:{password}".encode()).decode("ascii")
		return f"Basic {token}"

	def prometheus_session(self) -> _BaseUrlSession:
		"""
		Return a `requests.Session` pre-configured with the Prometheus base URL and auth.
		"""
		session = _BaseUrlSession(f"https://{self.name}/prometheus/")
		session.auth = HTTPBasicAuth(self.prometheus_username, self.get_password("grafana_password"))  # type: ignore
		return session

	@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
	def run_promql(self, query: str) -> list:
		"""Run an instant PromQL query and return the result list."""
		return PrometheusConnect(
			url=f"https://{self.name}/prometheus",
			auth=(self.prometheus_username, self.get_password("grafana_password")),
		).custom_query(query=query)

	def run_promql_scalar(self, query: str, val_type: type = float) -> float | int | None:
		"""Run an instant PromQL query and return the first scalar value cast to *type*.

		For `int` results the value is clamped to `max(0, value)`.
		For `float` results the value is rounded to 2 decimal places.
		Returns -1 if the query yields no data or raises an exception.
		"""
		try:
			result = self.run_promql(query)
			if result:
				value = float(result[0]["value"][1])
				if val_type is int:
					return max(0, int(round(value, 0)))
				if val_type is float:
					return round(value, 2)
				return value
		except Exception:
			pass
		return -1


@redis_cache(ttl=3600)
def get_monitor_server_ips():
	servers = frappe.get_all(
		"Monitor Server", filters={"status": ["!=", "Archived"]}, fields=["ip", "private_ip"]
	)
	ips = []
	for server in servers:
		if server.ip:
			ips.append(server.ip)
		if server.private_ip:
			ips.append(server.private_ip)
	return ips


def check_monitoring_servers_rate_limit_key():
	from press.api.monitoring import MONITORING_ENDPOINT_RATE_LIMIT_WINDOW_SECONDS
	from press.telegram_utils import Telegram

	ips = get_monitor_server_ips()

	for ip in ips:
		key = f"{frappe.conf.db_name}|rl:press.api.monitoring.targets:{ip}:{MONITORING_ENDPOINT_RATE_LIMIT_WINDOW_SECONDS}"
		val = frappe.cache.get(key)
		if not val:
			continue
		current_val = cint(val.decode("utf-8"))
		if current_val > 100:
			frappe.cache.delete(key)
			with contextlib.suppress(Exception):
				msg = f"Rate limit key for monitoring server {ip} had value {current_val} which is too high. Deleted the key.\n@adityahase @balamurali27 @tanmoysrt"
				Telegram("Errors").send(msg)
