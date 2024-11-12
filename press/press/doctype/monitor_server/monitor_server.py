# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json

import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


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
		hostname: DF.Data
		ip: DF.Data | None
		ip6: DF.Data | None
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		prometheus_data_directory: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_agent_password()
		self.validate_grafana_password()
		self.validate_monitoring_password()

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def validate_grafana_password(self):
		if not self.grafana_password:
			self.grafana_password = frappe.generate_hash(length=32)

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
