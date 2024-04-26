# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import json
import shlex
import typing
from functools import cached_property
from typing import List, Union

import boto3
import frappe
from frappe import _
from frappe.core.utils import find
from frappe.installer import subprocess
from frappe.model.document import Document
from frappe.utils.user import is_system_user

from press.agent import Agent
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.resource_tag.tag_helpers import TagHelpers
from press.runner import Ansible
from press.utils import log_error
from press.api.client import dashboard_whitelist

if typing.TYPE_CHECKING:
	from press.press.doctype.press_job.press_job import Bench


class BaseServer(Document, TagHelpers):
	dashboard_fields = [
		"title",
		"plan",
		"cluster",
		"status",
		"team",
		"database_server",
		"is_self_hosted",
	]

	@staticmethod
	def get_list_query(query):
		Server = frappe.qb.DocType("Server")

		query = query.where(Server.status != "Archived").where(
			Server.team == frappe.local.team().name
		)
		results = query.run(as_dict=True)

		for result in results:
			db_plan_name = frappe.db.get_value("Database Server", result.database_server, "plan")
			result.db_plan = (
				frappe.db.get_value(
					"Server Plan", db_plan_name, ["title", "price_inr", "price_usd"], as_dict=True
				)
				if db_plan_name
				else None
			)

		return results

	def get_doc(self, doc):
		from press.api.client import get
		from press.api.server import usage

		doc.current_plan = get("Server Plan", self.plan) if self.plan else None
		doc.usage = usage(self.name)
		doc.actions = self.get_actions()
		doc.disk_size = frappe.db.get_value(
			"Virtual Machine", self.virtual_machine, "disk_size"
		)

		return doc

	def get_actions(self):
		actions = [
			{
				"action": "Reboot server",
				"description": "Reboot the application server"
				if self.doctype == "Server"
				else "Reboot the database server",
				"button_label": "Reboot",
				"condition": self.status == "Active",
				"doc_method": "reboot",
			},
			{
				"action": "Rename server",
				"description": "Rename the application server"
				if self.doctype == "Server"
				else "Rename the database server",
				"button_label": "Rename",
				"condition": self.status == "Active",
				"doc_method": "rename",
			},
			{
				"action": "Drop server",
				"description": "Drop both the application and database servers",
				"button_label": "Drop",
				"condition": self.status == "Active" and self.doctype == "Server",
				"doc_method": "drop_server",
			},
		]
		return [action for action in actions if action.get("condition", True)]

	@dashboard_whitelist()
	def drop_server(self):
		if self.doctype == "Database Server":
			app_server_name = frappe.db.get_value(
				"Server", {"database_server": self.name}, "name"
			)
			app_server = frappe.get_doc("Server", app_server_name)
			db_server = self
		else:
			app_server = self
			db_server = frappe.get_doc("Database Server", self.database_server)

		app_server.archive()
		db_server.archive()

	def autoname(self):
		if not self.domain:
			self.domain = frappe.db.get_single_value("Press Settings", "domain")
		self.name = f"{self.hostname}.{self.domain}"
		if (
			self.doctype in ["Database Server", "Server", "Proxy Server"] and self.is_self_hosted
		):
			self.name = f"{self.hostname}.{self.self_hosted_server_domain}"

	def validate(self):
		self.validate_cluster()
		self.validate_agent_password()
		if self.doctype == "Database Server" and not self.self_hosted_mariadb_server:
			self.self_hosted_mariadb_server = self.private_ip

		if not self.hostname_abbreviation:
			self._set_hostname_abbreviation()

	def _set_hostname_abbreviation(self):
		self.hostname_abbreviation = get_hostname_abbreviation(self.hostname)

	def after_insert(self):
		if self.ip:
			if (
				self.doctype not in ["Database Server", "Server", "Proxy Server"]
				or not self.is_self_hosted
			):
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
		url = f"https://github.com/{repository_owner}/agent"
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
			elif self.provider == "OCI":
				ansible = Ansible(playbook="oci.yml", server=self, user="ubuntu")

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
			ansible = Ansible(
				playbook="nginx.yml",
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
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
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
			ansible = Ansible(
				playbook="ping.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
			)
			ansible.run()
		except Exception:
			log_error("Server Ping Exception", server=self.as_dict())

	@frappe.whitelist()
	def update_agent_ansible(self):
		frappe.enqueue_doc(self.doctype, self.name, "_update_agent_ansible")

	def _update_agent_ansible(self):
		try:
			ansible = Ansible(
				playbook="update_agent.yml",
				variables={"agent_repository_url": self.get_agent_repository_url()},
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
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
			elif self.provider in ("AWS EC2", "OCI"):
				ansible = Ansible(playbook="ping.yml", server=self, user="ubuntu")
			ansible.run()
		except Exception:
			log_error("Unprepared Server Ping Exception", server=self.as_dict())

	@frappe.whitelist()
	def cleanup_unused_files(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_cleanup_unused_files", queue="long", timeout=2400
		)

	def _cleanup_unused_files(self):
		agent = Agent(self.name, self.doctype)
		agent.cleanup_unused_files()

	def on_trash(self):
		plays = frappe.get_all("Ansible Play", filters={"server": self.name})
		for play in plays:
			frappe.delete_doc("Ansible Play", play.name)

	@frappe.whitelist()
	def extend_ec2_volume(self):
		if self.provider not in ("AWS EC2", "OCI"):
			return
		try:
			subprocess.check_output(shlex.split(f"ssh root@{self.ip} -t rm /root/glass"))
			ansible = Ansible(playbook="extend_ec2_volume.yml", server=self)
			ansible.run()
		except Exception:
			log_error("EC2 Volume Extend Exception", server=self.as_dict())

	@frappe.whitelist()
	def increase_disk_size(self, increment=50):
		if self.provider not in ("AWS EC2", "OCI"):
			return
		virtual_machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		virtual_machine.increase_disk_size(increment)
		self.extend_ec2_volume()

	def update_virtual_machine_name(self):
		if self.provider not in ("AWS EC2", "OCI"):
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
			"Subscription",
			{"document_type": self.doctype, "document_name": self.name, "team": self.team},
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
		if frappe.get_all(
			"Site",
			filters={"server": self.name, "status": ("!=", "Archived")},
			ignore_ifnull=True,
		):
			frappe.throw(_("Cannot archive server with sites"))
		if frappe.get_all(
			"Bench",
			filters={"server": self.name, "status": ("!=", "Archived")},
			ignore_ifnull=True,
		):
			frappe.throw(_("Cannot archive server with benches"))
		self.status = "Pending"
		self.save()
		if self.is_self_hosted:
			self.status = "Archived"
			self.save()

			if self.doctype == "Server":
				frappe.db.set_value(
					"Self Hosted Server", {"server": self.name}, "status", "Archived"
				)

		else:
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

		if team.parent_team:
			team = frappe.get_doc("Team", team.parent_team)

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

	@dashboard_whitelist()
	def change_plan(self, plan, ignore_card_setup=False):
		self.can_change_plan(ignore_card_setup)
		plan = frappe.get_doc("Server Plan", plan)
		self.ram = plan.memory
		self.save()
		self.reload()
		frappe.get_doc(
			{
				"doctype": "Plan Change",
				"document_type": self.doctype,
				"document_name": self.name,
				"from_plan": self.plan,
				"to_plan": plan.name,
			}
		).insert()
		self.run_press_job("Resize Server", {"machine_type": plan.instance_type})

	@frappe.whitelist()
	def create_image(self):
		self.run_press_job("Create Server Snapshot")

	def run_press_job(self, job_name, arguments=None):
		frappe.db.get_value(self.doctype, self.name, "status", for_update=True)
		if existing_jobs := frappe.db.get_all(
			"Press Job",
			{
				"status": ("in", ["Pending", "Running"]),
				"server_type": self.doctype,
				"server": self.name,
			},
			["job_type", "status"],
		):
			frappe.throw(
				f"A {existing_jobs[0].job_type} job is already {existing_jobs[0].status}. Please wait for the same."
			)

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

		if not certificate_name and self.is_self_hosted:
			certificate_name = frappe.db.get_value(
				"TLS Certificate", {"domain": f"{self.name}"}, "name"
			)

			if not certificate_name:
				self_hosted_server = frappe.db.get_value(
					"Self Hosted Server", {"server": self.name}, ["hostname", "domain"], as_dict=1
				)

				certificate_name = frappe.db.get_value(
					"TLS Certificate",
					{"domain": f"{self_hosted_server.hostname}.{self_hosted_server.domain}"},
					"name",
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

	@frappe.whitelist()
	def increase_swap(self, swap_size=4):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_increase_swap",
			queue="long",
			timeout=1200,
			**{"swap_size": swap_size},
		)

	def add_glass_file(self):
		frappe.enqueue_doc(self.doctype, self.name, "_add_glass_file")

	def _add_glass_file(self):
		try:
			ansible = Ansible(playbook="glass_file.yml", server=self)
			ansible.run()
		except Exception:
			log_error("Add Glass File Exception", server=self.as_dict())

	def _increase_swap(self, swap_size=4):
		"""Increase swap by size defined in playbook"""
		from press.api.server import calculate_swap

		existing_swap_size = calculate_swap(self.name).get("swap", 0)
		# We used to do 4 GB minimum swap files, to avoid conflict, name files accordingly
		swap_file_name = "swap" + str(int((existing_swap_size // 4) + 1))
		try:
			ansible = Ansible(
				playbook="increase_swap.yml",
				server=self,
				variables={
					"swap_size": swap_size,
					"swap_file": swap_file_name,
				},
			)
			ansible.run()
		except Exception:
			log_error("Increase swap exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_mysqldump(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_mysqldump")

	def _setup_mysqldump(self):
		try:
			ansible = Ansible(
				playbook="mysqldump.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("MySQLdump Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def set_swappiness(self):
		frappe.enqueue_doc(self.doctype, self.name, "_set_swappiness")

	def _set_swappiness(self):
		try:
			ansible = Ansible(
				playbook="swappiness.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Swappiness Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def update_tls_certificate(self):
		from press.press.doctype.tls_certificate.tls_certificate import (
			update_server_tls_certifcate,
		)

		certificate = frappe.get_last_doc(
			"TLS Certificate",
			{"wildcard": True, "domain": self.domain, "status": "Active"},
		)
		update_server_tls_certifcate(self, certificate)

	@frappe.whitelist()
	def show_agent_password(self):
		return self.get_password("agent_password")

	@property
	def agent(self):
		return Agent(self.name, server_type=self.doctype)

	@frappe.whitelist()
	def fetch_security_updates(self):
		from press.press.doctype.security_update.security_update import SecurityUpdate

		frappe.enqueue(SecurityUpdate.fetch_security_updates, server_obj=self)

	@frappe.whitelist()
	def configure_ssh_logging(self):
		try:
			ansible = Ansible(
				playbook="configure_ssh_logging.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Set SSH Session Logging Exception", server=self.as_dict())

	@property
	def real_ram(self):
		"""Ram detected by OS after h/w reservation"""
		return 0.972 * self.ram - 218

	@frappe.whitelist()
	def reboot_with_serial_console(self):
		if self.provider in ("AWS EC2",):
			console = frappe.new_doc("Serial Console Log")
			console.server_type = self.doctype
			console.server = self.name
			console.virtual_machine = self.virtual_machine
			console.save()
			console.reload()
			console.run_reboot()

	@dashboard_whitelist()
	def reboot(self):
		if self.provider in ("AWS EC2", "OCI"):
			virtual_machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
			virtual_machine.reboot()

	@dashboard_whitelist()
	def rename(self, title):
		self.title = title
		self.save()

	def wait_for_cloud_init(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_wait_for_cloud_init",
			queue="short",
		)

	def _wait_for_cloud_init(self):
		try:
			ansible = Ansible(
				playbook="wait_for_cloud_init.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Cloud Init Wait Exception", server=self.as_dict())


class Server(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.resource_tag.resource_tag import ResourceTag

		agent_password: DF.Password | None
		cluster: DF.Link | None
		database_server: DF.Link | None
		disable_agent_job_auto_retry: DF.Check
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		hostname_abbreviation: DF.Data | None
		ignore_incidents: DF.Check
		ip: DF.Data | None
		is_primary: DF.Check
		is_replication_setup: DF.Check
		is_self_hosted: DF.Check
		is_server_prepared: DF.Check
		is_server_renamed: DF.Check
		is_server_setup: DF.Check
		is_standalone: DF.Check
		is_standalone_setup: DF.Check
		is_upstream_setup: DF.Check
		new_worker_allocation: DF.Check
		plan: DF.Link | None
		primary: DF.Link | None
		private_ip: DF.Data | None
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		proxy_server: DF.Link | None
		ram: DF.Float
		root_public_key: DF.Code | None
		self_hosted_mariadb_root_password: DF.Password | None
		self_hosted_mariadb_server: DF.Data | None
		self_hosted_server_domain: DF.Data | None
		set_bench_memory_limits: DF.Check
		skip_scheduled_backups: DF.Check
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		staging: DF.Check
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tags: DF.Table[ResourceTag]
		team: DF.Link | None
		title: DF.Data | None
		use_for_new_benches: DF.Check
		use_for_new_sites: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	GUNICORN_MEMORY = 150  # avg ram usage of 1 gunicorn worker
	BACKGROUND_JOB_MEMORY = 3 * 80  # avg ram usage of 3 sets of bg workers

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

		if not self.is_new() and self.has_value_changed("team"):

			if self.subscription and self.subscription.team != self.team:
				self.subscription.disable()

				if subscription := frappe.db.get_value(
					"Subscription",
					{
						"document_type": self.doctype,
						"document_name": self.name,
						"team": self.team,
						"plan": self.plan,
					},
				):
					frappe.db.set_value("Subscription", subscription, "enabled", 1)
				else:
					try:
						# create new subscription
						frappe.get_doc(
							{
								"doctype": "Subscription",
								"document_type": self.doctype,
								"document_name": self.name,
								"team": self.team,
								"plan": self.plan,
							}
						).insert()
					except Exception:
						frappe.log_error("Server Subscription Creation Error")

	@frappe.whitelist()
	def add_upstream_to_proxy(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_server(self.name)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		certificate = self.get_certificate()
		log_server, kibana_password = self.get_log_server()
		proxy_ip = frappe.db.get_value("Proxy Server", self.proxy_server, "private_ip")

		try:
			ansible = Ansible(
				playbook="self_hosted.yml"
				if getattr(self, "is_self_hosted", False)
				else "server.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"proxy_ip": proxy_ip,
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
	def setup_standalone(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_standalone", queue="short", timeout=1200
		)

	def _setup_standalone(self):
		try:
			ansible = Ansible(
				playbook="standalone.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"domain": self.domain,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.is_standalone_setup = True
		except Exception:
			log_error("Standalone Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def whitelist_ipaddress(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_whitelist_ip", queue="short", timeout=1200
		)

	def _whitelist_ip(self):
		proxy_server = frappe.get_value("Server", self.name, "proxy_server")
		proxy_server_ip = frappe.get_doc("Proxy Server", proxy_server).ip

		try:
			ansible = Ansible(
				playbook="whitelist_ipaddress.yml",
				server=self,
				variables={"ip_address": proxy_server_ip},
			)
			play = ansible.run()
			self.reload()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Proxy IP Whitelist Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def agent_set_proxy_ip(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_agent_set_proxy_ip", queue="short", timeout=1200
		)

	def _agent_set_proxy_ip(self):
		proxy_ip = frappe.db.get_value("Proxy Server", self.proxy_server, "private_ip")
		agent_password = self.get_password("agent_password")

		try:
			ansible = Ansible(
				playbook="agent_set_proxy_ip.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"proxy_ip": proxy_ip,
					"workers": "2",
					"agent_password": agent_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Agent Proxy IP Setup Exception", server=self.as_dict())
		self.save()

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

		proxy_ip = frappe.db.get_value("Proxy Server", self.proxy_server, "private_ip")

		try:
			ansible = Ansible(
				playbook="rename.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"proxy_ip": proxy_ip,
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

	@frappe.whitelist()
	def auto_scale_workers(self, commit=True):
		if self.new_worker_allocation:
			self._auto_scale_workers_new(commit)
		else:
			self._auto_scale_workers_old()

	@cached_property
	def bench_workloads(self) -> dict["Bench", int]:
		bench_workloads = {}
		benches = frappe.get_all(
			"Bench",
			filters={"server": self.name, "status": "Active", "auto_scale_workers": True},
			pluck="name",
		)
		for bench_name in benches:
			bench = frappe.get_doc("Bench", bench_name, for_update=True)
			bench_workloads[bench] = bench.workload
		return bench_workloads

	@cached_property
	def workload(self) -> int:
		return sum(self.bench_workloads.values())

	@cached_property
	def usable_ram(self) -> float:
		return max(
			self.ram - 3000, self.ram * 0.75
		)  # in MB (leaving some for disk cache + others)

	@cached_property
	def max_gunicorn_workers(self) -> int:
		usable_ram_for_gunicorn = 0.6 * self.usable_ram  # 60% of usable ram
		return usable_ram_for_gunicorn / self.GUNICORN_MEMORY

	@cached_property
	def max_bg_workers(self) -> int:
		usable_ram_for_bg = 0.4 * self.usable_ram  # 40% of usable ram
		return usable_ram_for_bg / self.BACKGROUND_JOB_MEMORY

	def _auto_scale_workers_new(self, commit):
		for bench in self.bench_workloads.keys():
			try:
				bench.allocate_workers(
					self.workload,
					self.max_gunicorn_workers,
					self.max_bg_workers,
					self.set_bench_memory_limits,
					self.GUNICORN_MEMORY,
					self.BACKGROUND_JOB_MEMORY,
				)
				if commit:
					frappe.db.commit()
			except Exception:
				log_error(
					"Bench Auto Scale Worker Error", bench=bench, workload=self.bench_workloads[bench]
				)
				if commit:
					frappe.db.rollback()

	def _auto_scale_workers_old(self):
		benches = frappe.get_all(
			"Bench",
			filters={"server": self.name, "status": "Active", "auto_scale_workers": True},
			pluck="name",
		)
		for bench_name in benches:
			bench = frappe.get_doc("Bench", bench_name)
			workload = bench.workload

			if workload <= 10:
				background_workers, gunicorn_workers = 1, 2
			elif workload <= 20:
				background_workers, gunicorn_workers = 2, 4
			elif workload <= 30:
				background_workers, gunicorn_workers = 3, 6
			elif workload <= 50:
				background_workers, gunicorn_workers = 4, 8
			elif workload <= 100:
				background_workers, gunicorn_workers = 6, 12
			elif workload <= 250:
				background_workers, gunicorn_workers = 8, 16
			elif workload <= 500:
				background_workers, gunicorn_workers = 16, 32
			else:
				background_workers, gunicorn_workers = 24, 48

			if (bench.background_workers, bench.gunicorn_workers) != (
				background_workers,
				gunicorn_workers,
			):
				bench = frappe.get_doc("Bench", bench.name)
				bench.background_workers, bench.gunicorn_workers = (
					background_workers,
					gunicorn_workers,
				)
				bench.save()

	@frappe.whitelist()
	def reset_sites_usage(self):
		sites = frappe.get_all(
			"Site",
			filters={"server": self.name, "status": "Active"},
			pluck="name",
		)
		for site_name in sites:
			site = frappe.get_doc("Site", site_name)
			site.reset_site_usage()

	def install_earlyoom(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_install_earlyoom",
		)

	def _install_earlyoom(self):
		try:
			ansible = Ansible(
				playbook="server_memory_limits.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Earlyoom Install Exception", server=self.as_dict())

	@property
	def is_shared(self) -> bool:
		public_groups = frappe.get_all("Release Group", {"public": True}, pluck="name")
		return bool(
			frappe.db.exists(
				"Release Group Server", {"server": self.name, "parent": ("in", public_groups)}
			)
		)


def scale_workers():
	servers = frappe.get_all("Server", {"status": "Active", "is_primary": True})
	for server in servers:
		try:
			frappe.get_doc("Server", server.name).auto_scale_workers()
			frappe.db.commit()
		except Exception:
			log_error("Auto Scale Worker Error", server=server)
			frappe.db.rollback()


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


def get_hostname_abbreviation(hostname):
	hostname_parts = hostname.split("-")

	abbr = hostname_parts[0]

	for part in hostname_parts[1:]:
		abbr += part[0]

	return abbr


def is_dedicated_server(server_name):
	if not isinstance(server_name, str):
		frappe.throw("Invalid argument")
	team = frappe.db.get_value("Server", server_name, "team") or ""
	return "@erpnext.com" not in team
