# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.agent import Agent
from press.utils import log_error
from frappe.utils import unique
from frappe.core.utils import find

import boto3


class ProxyServer(BaseServer):
	def validate(self):
		super().validate()
		self.validate_domains()
		self.validate_proxysql_admin_password()

	def validate_domains(self):
		domains = [row.domain for row in self.domains]
		# Always include self.domain in the domains child table
		# Remove duplicates
		domains = unique([self.domain] + domains)
		self.domains = []
		for domain in domains:
			if not frappe.db.exists(
				"TLS Certificate", {"wildcard": True, "status": "Active", "domain": domain}
			):
				frappe.throw(f"Valid wildcard TLS Certificate not found for {domain}")
			self.append("domains", {"domain": domain})

	def validate_proxysql_admin_password(self):
		if not self.proxysql_admin_password:
			self.proxysql_admin_password = frappe.generate_hash(length=32)

	def get_wildcard_domains(self):
		wildcard_domains = []
		for domain in self.domains:
			if domain.domain == self.domain:
				# self.domain certs are symlinks
				continue
			certificate_name = frappe.db.get_value(
				"TLS Certificate", {"wildcard": True, "domain": domain.domain}, "name"
			)
			certificate = frappe.get_doc("TLS Certificate", certificate_name)
			wildcard_domains.append(
				{
					"domain": domain.domain,
					"certificate": {
						"privkey.pem": certificate.private_key,
						"fullchain.pem": certificate.full_chain,
						"chain.pem": certificate.intermediate_chain,
					},
				}
			)
		return wildcard_domains

	@frappe.whitelist()
	def setup_wildcard_hosts(self):
		agent = Agent(self.name, server_type="Proxy Server")
		wildcards = self.get_wildcard_domains()
		agent.setup_wildcard_hosts(wildcards)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password(
			"monitoring_password"
		)

		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password(
				"kibana_password"
			)
		else:
			kibana_password = None

		try:
			ansible = Ansible(
				playbook="self_hosted_proxy.yml"
				if getattr(self, "is_self_hosted", False)
				else "proxy.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"monitoring_password": monitoring_password,
					"log_server": log_server,
					"kibana_password": kibana_password,
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
			log_error("Proxy Server Setup Exception", server=self.as_dict())
		self.save()

	def _install_exporters(self):
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password(
			"monitoring_password"
		)
		try:
			ansible = Ansible(
				playbook="proxy_exporters.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"private_ip": self.private_ip,
					"monitoring_password": monitoring_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Exporters Install Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_ssh_proxy(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_ssh_proxy", queue="long", timeout=1200
		)

	def _setup_ssh_proxy(self):
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)
		ca = frappe.get_doc("SSH Certificate Authority", self.ssh_certificate_authority)
		try:
			ansible = Ansible(
				playbook="ssh_proxy.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"registry_url": settings.docker_registry_url,
					"registry_username": settings.docker_registry_username,
					"registry_password": settings.docker_registry_password,
					"docker_image": ca.docker_image,
				},
			)
			play = ansible.run()
			if play.status == "Success":
				self.reload()
				self.is_ssh_proxy_setup = True
				self.save()
		except Exception:
			log_error("SSH Proxy Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_fail2ban(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_fail2ban", queue="long", timeout=1200
		)

	def _setup_fail2ban(self):
		try:
			ansible = Ansible(
				playbook="fail2ban.yml",
				server=self,
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Fail2ban Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def setup_proxysql(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_proxysql", queue="long", timeout=1200
		)

	def _setup_proxysql(self):
		try:
			default_hostgroup = frappe.get_all(
				"Database Server",
				"MIN(server_id)",
				{"status": "Active", "cluster": self.cluster},
				as_list=True,
			)[0][0]
			ansible = Ansible(
				playbook="proxysql.yml",
				server=self,
				variables={
					"server": self.name,
					"proxysql_admin_password": self.get_password("proxysql_admin_password"),
					"default_hostgroup": default_hostgroup,
				},
			)
			play = ansible.run()
			if play.status == "Success":
				self.reload()
				self.is_proxysql_setup = True
				self.save()
		except Exception:
			log_error("ProxySQL Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_replication(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_replication", queue="long", timeout=1200
		)

	def _setup_replication(self):
		self._setup_secondary()
		if self.status == "Active":
			primary = frappe.get_doc("Proxy Server", self.primary)
			primary._setup_primary(self.name)
			if primary.status == "Active":
				self.is_replication_setup = True
				self.save()

	def _setup_primary(self, secondary):
		secondary_private_ip = frappe.db.get_value("Proxy Server", secondary, "private_ip")
		try:
			ansible = Ansible(
				playbook="primary_proxy.yml",
				server=self,
				variables={"secondary_private_ip": secondary_private_ip},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Primary Proxy Server Setup Exception", server=self.as_dict())
		self.save()

	def _setup_secondary(self):
		primary_public_key = frappe.db.get_value(
			"Proxy Server", self.primary, "frappe_public_key"
		)
		try:
			ansible = Ansible(
				playbook="secondary_proxy.yml",
				server=self,
				variables={"primary_public_key": primary_public_key},
			)
			play = ansible.run()
			self.reload()

			if play.status == "Success":
				self.status = "Active"
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Secondary Proxy Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def trigger_failover(self):
		if self.is_primary:
			return
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_trigger_failover", queue="long", timeout=1200
		)

	def _trigger_failover(self):
		try:
			self.update_dns_record()
			self.reload_nginx()
			self.update_app_servers()
			self.switch_primary()
		except Exception:
			self.status = "Broken"
			log_error("Proxy Server Failover Exception", server=self.as_dict())
		self.save()

	def update_dns_record(self):
		try:
			domain = frappe.get_doc("Root Domain", self.domain)
			client = boto3.client(
				"route53",
				aws_access_key_id=domain.aws_access_key_id,
				aws_secret_access_key=domain.get_password("aws_secret_access_key"),
			)
			zones = client.list_hosted_zones_by_name()["HostedZones"]
			# list_hosted_zones_by_name returns a lexicographically ordered list of zones
			# i.e. x.example.com comes after example.com
			# Name field has a trailing dot
			hosted_zone = find(reversed(zones), lambda x: domain.name.endswith(x["Name"][:-1]))[
				"Id"
			]
			client.change_resource_record_sets(
				ChangeBatch={
					"Changes": [
						{
							"Action": "UPSERT",
							"ResourceRecordSet": {
								"Name": self.primary,
								"Type": "CNAME",
								"TTL": 3600,
								"ResourceRecords": [{"Value": self.name}],
							},
						}
					]
				},
				HostedZoneId=hosted_zone,
			)
		except Exception:
			self.status = "Broken"
			log_error("Route 53 Record Update Error", domain=domain.name, server=self.name)

	def reload_nginx(self):
		agent = Agent(self.name, server_type="Proxy Server")
		agent.restart_nginx()

	def update_app_servers(self):
		frappe.db.set_value(
			"Server", {"proxy_server": self.primary}, "proxy_server", self.name
		)

	def switch_primary(self):
		primary = frappe.get_doc("Proxy Server", self.primary)
		self.is_primary = True
		primary.is_primary = False
		primary.save()

	@frappe.whitelist()
	def setup_proxysql_monitor(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_proxysql_monitor", queue="long", timeout=1200
		)

	def _setup_proxysql_monitor(self):
		try:
			default_hostgroup = frappe.get_all(
				"Database Server",
				"MIN(server_id)",
				{"status": "Active", "cluster": self.cluster},
				as_list=True,
			)[0][0]
			ansible = Ansible(
				playbook="proxysql_monitor.yml",
				server=self,
				variables={
					"server": self.name,
					"proxysql_admin_password": self.get_password("proxysql_admin_password"),
					"default_hostgroup": default_hostgroup,
				},
			)
			ansible.run()
		except Exception:
			log_error("ProxySQL Monitor Setup Exception", server=self.as_dict())


def process_update_nginx_job_update(job):
	proxy_server = frappe.get_doc("Proxy Server", job.server)
	if job.status == "Success":
		proxy_server.status = "Active"
	elif job.status in ["Failure", "Undelivered"]:
		proxy_server.status = "Broken"
	elif job.status in ["Pending", "Running"]:
		proxy_server.status = "Installing"
	proxy_server.save()
