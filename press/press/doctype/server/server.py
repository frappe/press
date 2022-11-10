# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.agent import Agent
from press.runner import Ansible
from press.utils import log_error
from frappe.core.utils import find
from press.overrides import get_permission_query_conditions_for_doctype
from frappe.utils.user import is_system_user

from typing import List, Union
import boto3
import json


class BaseServer(Document):
	def autoname(self):
		if not self.domain:
			self.domain = frappe.db.get_single_value("Press Settings", "domain")
		self.name = f"{self.hostname}.{self.domain}"

	def validate(self):
		self.validate_cluster()
		self.validate_agent_password()

	def after_insert(self):
		if self.ip:
			self.create_dns_record()
			self.update_virtual_machine_name()

	def create_dns_record(self):
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
								"Name": self.name,
								"Type": "A",
								"TTL": 3600 if self.doctype == "Proxy Server" else 300,
								"ResourceRecords": [{"Value": self.ip}],
							},
						}
					]
				},
				HostedZoneId=hosted_zone,
			)
		except Exception:
			log_error("Route 53 Record Creation Error", domain=domain.name, server=self.name)

	def validate_cluster(self):
		if not self.cluster:
			self.cluster = frappe.db.get_value("Root Domain", self.domain, "default_cluster")
		if not self.cluster:
			frappe.throw("Default Cluster not found", frappe.ValidationError)

	def validate_agent_password(self):
		if not self.agent_password:
			self.agent_password = frappe.generate_hash(length=32)

	def get_agent_repository_url(self):
		settings = frappe.get_single("Press Settings")
		repository_owner = settings.agent_repository_owner or "frappe"
		token = settings.agent_github_access_token
		url = f"https://x-access-token:{token}@github.com/{repository_owner}/agent"
		return url

	@frappe.whitelist()
	def ping_agent(self):
		agent = Agent(self.name, self.doctype)
		return agent.ping()

	@frappe.whitelist()
	def update_agent(self):
		agent = Agent(self.name, self.doctype)
		return agent.update()

	@frappe.whitelist()
	def prepare_server(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_prepare_server", queue="long", timeout=2400
		)

	def _prepare_server(self):
		try:
			if self.provider == "Scaleway":
				ansible = Ansible(
					playbook="scaleway.yml",
					server=self,
					user="ubuntu",
					variables={
						"private_ip": self.private_ip,
						"private_mac_address": self.private_mac_address,
						"private_vlan_id": self.private_vlan_id,
					},
				)
			elif self.provider == "AWS EC2":
				ansible = Ansible(playbook="aws.yml", server=self, user="ubuntu")

			ansible.run()
			self.reload()
			self.is_server_prepared = True
			self.save()
		except Exception:
			log_error("Server Preparation Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_server", queue="long", timeout=2400
		)

	@frappe.whitelist()
	def install_nginx(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_install_nginx", queue="long", timeout=1200
		)

	def _install_nginx(self):
		try:
			ansible = Ansible(playbook="nginx.yml", server=self)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("NGINX Install Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def install_filebeat(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_install_filebeat", queue="long", timeout=1200
		)

	def _install_filebeat(self):
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password(
				"kibana_password"
			)
		else:
			kibana_password = None

		try:
			ansible = Ansible(
				playbook="filebeat.yml",
				server=self,
				variables={
					"server": self.name,
					"log_server": log_server,
					"kibana_password": kibana_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Filebeat Install Exception", server=self.as_dict())

	@frappe.whitelist()
	def install_exporters(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_install_exporters", queue="long", timeout=1200
		)

	@frappe.whitelist()
	def ping_ansible(self):
		try:
			ansible = Ansible(playbook="ping.yml", server=self)
			ansible.run()
		except Exception:
			log_error("Server Ping Exception", server=self.as_dict())

	@frappe.whitelist()
	def update_agent_ansible(self):
		try:
			ansible = Ansible(
				playbook="update_agent.yml",
				variables={"agent_repository_url": self.get_agent_repository_url()},
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Agent Update Exception", server=self.as_dict())

	@frappe.whitelist()
	def fetch_keys(self):
		try:
			ansible = Ansible(playbook="keys.yml", server=self)
			ansible.run()
		except Exception:
			log_error("Server Key Fetch Exception", server=self.as_dict())

	@frappe.whitelist()
	def ping_ansible_unprepared(self):
		try:
			if self.provider == "Scaleway":
				ansible = Ansible(
					playbook="ping.yml",
					server=self,
					user="ubuntu",
				)
			elif self.provider == "AWS EC2":
				ansible = Ansible(playbook="ping.yml", server=self, user="ubuntu")
			ansible.run()
		except Exception:
			log_error("Unprepared Server Ping Exception", server=self.as_dict())

	def cleanup_unused_files(self):
		agent = Agent(self.name, self.doctype)
		agent.cleanup_unused_files()

	def on_trash(self):
		plays = frappe.get_all("Ansible Play", filters={"server": self.name})
		for play in plays:
			frappe.delete_doc("Ansible Play", play.name)

	@frappe.whitelist()
	def extend_ec2_volume(self):
		if self.provider != "AWS EC2":
			return
		try:
			ansible = Ansible(playbook="extend_ec2_volume.yml", server=self)
			ansible.run()
		except Exception:
			log_error("EC2 Volume Extend Exception", server=self.as_dict())

	@frappe.whitelist()
	def increase_disk_size(self, increment=50):
		if self.provider != "AWS EC2":
			return
		virtual_machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		virtual_machine.increase_disk_size(increment)
		self.extend_ec2_volume()

	def update_virtual_machine_name(self):
		if self.provider != "AWS EC2":
			return
		virtual_machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		return virtual_machine.update_name_tag(self.name)

	def create_subscription(self, plan):
		self._create_initial_plan_change(plan)

	def _create_initial_plan_change(self, plan):
		frappe.get_doc(
			{
				"doctype": "Plan Change",
				"document_type": self.doctype,
				"document_name": self.name,
				"from_plan": "",
				"to_plan": plan,
				"type": "Initial Plan",
				"timestamp": self.creation,
			}
		).insert(ignore_permissions=True)

	@property
	def subscription(self):
		name = frappe.db.get_value(
			"Subscription", {"document_type": self.doctype, "document_name": self.name}
		)
		return frappe.get_doc("Subscription", name) if name else None

	@frappe.whitelist()
	def rename_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_rename_server", queue="long", timeout=2400
		)

	@frappe.whitelist()
	def archive(self):
		self.status = "Pending"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_archive", queue="long")
		self.disable_subscription()

	def _archive(self):
		self.run_press_job("Archive Server")

	def disable_subscription(self):
		subscription = self.subscription
		if subscription:
			subscription.disable()

	def can_change_plan(self, ignore_card_setup):
		if is_system_user(frappe.session.user):
			return

		if ignore_card_setup:
			return

		team = frappe.get_doc("Team", self.team)

		if team.is_defaulter():
			frappe.throw("Cannot change plan because you have unpaid invoices")

		if team.payment_mode == "Partner Credits" and (
			not team.get_available_partner_credits() > 0
		):
			frappe.throw("Cannot change plan because you don't have sufficient partner credits")

		if team.payment_mode != "Partner Credits" and not (
			team.default_payment_method or team.get_balance()
		):
			frappe.throw(
				"Cannot change plan because you haven't added a card and not have enough balance"
			)

	def change_plan(self, plan, ignore_card_setup=False):
		self.can_change_plan(ignore_card_setup)
		frappe.get_doc(
			{
				"doctype": "Plan Change",
				"document_type": self.doctype,
				"document_name": self.name,
				"from_plan": self.plan,
				"to_plan": plan,
			}
		).insert()
		machine_type = frappe.db.get_value("Plan", plan, "instance_type")
		self.run_press_job("Resize Server", {"machine_type": machine_type})

	@frappe.whitelist()
	def create_image(self):
		self.run_press_job("Create Server Snapshot")

	def run_press_job(self, job_name, arguments=None):
		if arguments is None:
			arguments = {}
		return frappe.get_doc(
			{
				"doctype": "Press Job",
				"job_type": job_name,
				"server_type": self.doctype,
				"server": self.name,
				"virtual_machine": self.virtual_machine,
				"arguments": json.dumps(arguments, indent=2, sort_keys=True),
			}
		).insert()

	def get_certificate(self):
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		return frappe.get_doc("TLS Certificate", certificate_name)

	def get_log_server(self):
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password(
				"kibana_password"
			)
		else:
			kibana_password = None
		return log_server, kibana_password

	def get_monitoring_password(self):
		return frappe.get_doc("Cluster", self.cluster).get_password("monitoring_password")


class Server(BaseServer):
	def on_update(self):
		# If Database Server is changed for the server then change it for all the benches
		if not self.is_new() and self.has_value_changed("database_server"):
			benches = frappe.get_all(
				"Bench", {"server": self.name, "status": ("!=", "Archived")}
			)
			for bench in benches:
				bench = frappe.get_doc("Bench", bench)
				bench.database_server = self.database_server
				bench.save()

	@frappe.whitelist()
	def add_upstream_to_proxy(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_server(self.name)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		certificate = self.get_certificate()
		log_server, kibana_password = self.get_log_server()

		try:
			ansible = Ansible(
				playbook="server.yml",
				server=self,
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"workers": "2",
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"monitoring_password": self.get_monitoring_password(),
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
			log_error("Server Setup Exception", server=self.as_dict())
		self.save()

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
			primary = frappe.get_doc("Server", self.primary)
			primary._setup_primary(self.name)
			if primary.status == "Active":
				self.is_replication_setup = True
				self.save()

	def _setup_primary(self, secondary):
		secondary_private_ip = frappe.db.get_value("Server", secondary, "private_ip")
		try:
			ansible = Ansible(
				playbook="primary_app.yml",
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
			log_error("Primary Server Setup Exception", server=self.as_dict())
		self.save()

	def _setup_secondary(self):
		primary_public_key = frappe.db.get_value("Server", self.primary, "frappe_public_key")
		try:
			ansible = Ansible(
				playbook="secondary_app.yml",
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
			log_error("Secondary Server Setup Exception", server=self.as_dict())
		self.save()

	def _install_exporters(self):
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password(
			"monitoring_password"
		)
		try:
			ansible = Ansible(
				playbook="server_exporters.yml",
				server=self,
				variables={
					"private_ip": self.private_ip,
					"monitoring_password": monitoring_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Exporters Install Exception", server=self.as_dict())

	@classmethod
	def get_all_prod(cls, **kwargs) -> List[str]:
		"""Active prod servers."""
		return frappe.get_all("Server", {"status": "Active"}, pluck="name", **kwargs)

	@classmethod
	def get_all_primary_prod(cls) -> List[str]:
		"""Active primary prod servers."""
		return frappe.get_all(
			"Server", {"status": "Active", "is_primary": True}, pluck="name"
		)

	@classmethod
	def get_all_staging(cls, **kwargs) -> List[str]:
		"""Active staging servers."""
		return frappe.get_all(
			"Server", {"status": "Active", "staging": True}, pluck="name", **kwargs
		)

	@classmethod
	def get_one_staging(cls) -> str:
		return cls.get_all_staging(limit=1)[0]

	@classmethod
	def get_prod_for_new_bench(cls, extra_filters={}) -> Union[str, None]:
		filters = {"status": "Active", "use_for_new_benches": True}
		servers = frappe.get_all(
			"Server", {**filters, **extra_filters}, pluck="name", limit=1
		)
		if servers:
			return servers[0]

	@frappe.whitelist()
	def reboot(self):
		if self.provider == "AWS EC2":
			virtual_machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
			virtual_machine.reboot()

	def _rename_server(self):
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
				playbook="rename.yml",
				server=self,
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"workers": "2",
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
				self.is_server_renamed = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Server Rename Exception", server=self.as_dict())
		self.save()


def process_new_server_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Server", job.upstream, "is_upstream_setup", True)


def cleanup_unused_files():
	servers = frappe.get_all("Server", fields=["name"], filters={"status": "Active"})
	for server in servers:
		try:
			frappe.get_doc("Server", server.name).cleanup_unused_files()
		except Exception:
			log_error("Server File Cleanup Error", server=server)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Server")
