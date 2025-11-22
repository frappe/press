# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import contextlib
import json
from typing import TypedDict

import frappe
import requests
from frappe.utils.caching import redis_cache
from frappe.utils.data import cint
from requests.auth import HTTPBasicAuth

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class SitesDownAlertLabels(TypedDict):
	alertname: str
	bench: str
	cluster: str
	group: str
	instance: str
	job: str
	server: str
	severity: str


class SitesDownAlert(TypedDict):
	labels: SitesDownAlertLabels


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
	def show_grafana_password(self):
		return self.get_password("grafana_password")

	@property
	def alerts(self):
		print(
			f"https://{self.name}/prometheus/api/v1/rules",
		)
		ret = requests.get(
			f"https://{self.name}/prometheus/api/v1/rules",
			auth=HTTPBasicAuth(self.prometheus_username, self.get_password("grafana_password")),
			params={"type": "alert"},
		)

		ret.raise_for_status()
		data = ret.json()
		if data["status"] != "success":
			frappe.throw("Error fetching sites down")
		return data["data"]["groups"][0]["rules"]

	@property
	def sites_down_alerts(self) -> list[SitesDownAlert]:
		for alert in self.alerts:
			if not (alert["name"] == "Sites Down" and alert["state"] == "firing"):
				continue
			return alert["alerts"]
		return []

	@property
	def sites_down(self):
		sites = []
		for alert in self.sites_down_alerts:
			sites.append(alert["labels"]["instance"])
		return sites

	def get_sites_down_for_server(self, server: str) -> list[str]:
		sites = []
		for alert in self.sites_down_alerts:
			if alert["labels"]["server"] == server:
				sites.append(alert["labels"]["instance"])
		return sites

	@property
	def benches_down(self):
		benches = []
		for alert in self.sites_down_alerts:
			benches.append(alert["labels"]["bench"])
		return set(benches)

	def get_benches_down_for_server(self, server: str) -> set[str]:
		benches = []
		for alert in self.sites_down_alerts:
			if alert["labels"]["server"] == server:
				benches.append(alert["labels"]["bench"])
		return set(benches)


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
