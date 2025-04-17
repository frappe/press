# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import shlex
import typing
from contextlib import suppress
from datetime import timedelta
from functools import cached_property

import boto3
import frappe
from frappe import _
from frappe.core.utils import find, find_all
from frappe.installer import subprocess
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.synchronization import filelock
from frappe.utils.user import is_system_user

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.exceptions import VolumeResizeLimitError
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.resource_tag.tag_helpers import TagHelpers
from press.runner import Ansible
from press.telegram_utils import Telegram
from press.utils import fmt_timedelta, log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.ansible_play.ansible_play import AnsiblePlay
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class BaseServer(Document, TagHelpers):
	dashboard_fields = (
		"title",
		"plan",
		"cluster",
		"status",
		"team",
		"database_server",
		"is_self_hosted",
		"auto_add_storage_min",
		"auto_add_storage_max",
	)

	@staticmethod
	def get_list_query(query):
		Server = frappe.qb.DocType("Server")

		query = query.where(Server.status != "Archived").where(Server.team == frappe.local.team().name)
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

		if self.plan:
			doc.current_plan = get("Server Plan", self.plan)
		else:
			if virtual_machine := frappe.db.get_value(
				"Virtual Machine", self.virtual_machine, ["vcpu", "ram", "disk_size"], as_dict=True
			):
				doc.current_plan = {
					"vcpu": virtual_machine.vcpu,
					"memory": virtual_machine.ram,
					"disk": virtual_machine.disk_size,
				}

		doc.storage_plan = frappe.db.get_value(
			"Server Storage Plan",
			{"enabled": 1},
			["price_inr", "price_usd"],
			as_dict=True,
		)
		doc.usage = usage(self.name)
		doc.actions = self.get_actions()
		doc.disk_size = frappe.db.get_value("Virtual Machine", self.virtual_machine, "disk_size")
		doc.replication_server = frappe.db.get_value(
			"Database Server",
			{"primary": doc.database_server, "is_replication_setup": 1},
			"name",
		)
		doc.owner_email = frappe.db.get_value("Team", self.team, "user")

		return doc

	@dashboard_whitelist()
	def increase_disk_size_for_server(
		self, server: str, increment: int, mountpoint: str | None = None
	) -> None:
		if server == self.name:
			self.increase_disk_size(increment=increment, mountpoint=mountpoint)
			self.create_subscription_for_storage(increment)
		else:
			server_doc = frappe.get_doc("Database Server", server)
			server_doc.increase_disk_size(increment=increment, mountpoint=mountpoint)
			server_doc.create_subscription_for_storage(increment)

	@dashboard_whitelist()
	def configure_auto_add_storage(self, server: str, min: int, max: int) -> None:
		if min < 0 or max < 0:
			frappe.throw(_("Minimum and maximum storage sizes must be positive"))
		if min > max:
			frappe.throw(_("Minimum storage size must be less than the maximum storage size"))

		if server == self.name:
			self.auto_add_storage_min = min
			self.auto_add_storage_max = max
			self.save()
		else:
			server_doc = frappe.get_doc("Database Server", server)
			server_doc.auto_add_storage_min = min
			server_doc.auto_add_storage_max = max
			server_doc.save()

	@staticmethod
	def on_not_found(name):
		# If name is of a db server then redirect to the app server
		app_server = frappe.db.get_value("Server", {"database_server": name}, "name")
		if app_server:
			frappe.response.message = {
				"redirect": f"/dashboard/servers/{app_server}",
			}
		raise

	def get_actions(self):
		server_type = ""
		if self.doctype == "Server":
			server_type = "application server"
		elif self.doctype == "Database Server":
			if self.is_replication_setup:
				server_type = "replication server"
			else:
				server_type = "database server"

		actions = [
			{
				"action": "Rename server",
				"description": f"Rename the {server_type}",
				"button_label": "Rename",
				"condition": self.status == "Active",
				"doc_method": "rename",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Reboot server",
				"description": f"Reboot the {server_type}",
				"button_label": "Reboot",
				"condition": self.status == "Active",
				"doc_method": "reboot",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Drop server",
				"description": "Drop both the application and database servers",
				"button_label": "Drop",
				"condition": self.status == "Active" and self.doctype == "Server",
				"doc_method": "drop_server",
				"group": "Dangerous Actions",
			},
		]

		for action in actions:
			action["server_doctype"] = self.doctype
			action["server_name"] = self.name

		return [action for action in actions if action.get("condition", True)]

	@dashboard_whitelist()
	def drop_server(self):
		if self.doctype == "Database Server":
			app_server_name = frappe.db.get_value("Server", {"database_server": self.name}, "name")
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
		if self.doctype in ["Database Server", "Server", "Proxy Server"] and self.is_self_hosted:
			self.name = f"{self.hostname}.{self.self_hosted_server_domain}"

	def validate(self):
		self.validate_cluster()
		self.validate_agent_password()
		if self.doctype == "Database Server" and not self.self_hosted_mariadb_server:
			self.self_hosted_mariadb_server = self.private_ip

		if not self.hostname_abbreviation:
			self._set_hostname_abbreviation()

		self.validate_mounts()

	def _set_hostname_abbreviation(self):
		self.hostname_abbreviation = get_hostname_abbreviation(self.hostname)

	def after_insert(self):
		if self.ip and (
			self.doctype not in ["Database Server", "Server", "Proxy Server"] or not self.is_self_hosted
		):
			self.create_dns_record()
			self.update_virtual_machine_name()

	def create_dns_record(self):
		try:
			domain = frappe.get_doc("Root Domain", self.domain)

			if domain.generic_dns_provider:
				return

			client = boto3.client(
				"route53",
				aws_access_key_id=domain.aws_access_key_id,
				aws_secret_access_key=domain.get_password("aws_secret_access_key"),
			)
			zones = client.list_hosted_zones_by_name()["HostedZones"]
			# list_hosted_zones_by_name returns a lexicographically ordered list of zones
			# i.e. x.example.com comes after example.com
			# Name field has a trailing dot
			hosted_zone = find(reversed(zones), lambda x: domain.name.endswith(x["Name"][:-1]))["Id"]
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

	def add_server_to_public_groups(self):
		groups = frappe.get_all("Release Group", {"public": True, "enabled": True}, "name")
		for group_name in groups:
			group: ReleaseGroup = frappe.get_doc("Release Group", group_name)
			with suppress(frappe.ValidationError):
				group.add_server(str(self.name), deploy=True)

	@frappe.whitelist()
	def enable_server_for_new_benches_and_site(self):
		if not self.public:
			frappe.throw("Action only allowed for public servers")

		self.add_server_to_public_groups()
		server = self.get_server_enabled_for_new_benches_and_sites()

		if server:
			frappe.msgprint(_("Server {0} is already enabled for new benches and sites").format(server))

		else:
			self.use_for_new_benches = True
			self.use_for_new_sites = True
			self.save()

	def get_server_enabled_for_new_benches_and_sites(self):
		return frappe.db.get_value(
			"Server",
			{
				"name": ("!=", self.name),
				"is_primary": True,
				"status": "Active",
				"use_for_new_benches": True,
				"use_for_new_sites": True,
				"public": True,
				"cluster": self.cluster,
			},
			pluck=True,
		)

	@frappe.whitelist()
	def disable_server_for_new_benches_and_site(self):
		self.use_for_new_benches = False
		self.use_for_new_sites = False
		self.save()

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
		return f"https://github.com/{repository_owner}/agent"

	def get_agent_repository_branch(self):
		settings = frappe.get_single("Press Settings")
		return settings.branch or "master"

	@frappe.whitelist()
	def ping_agent(self):
		agent = Agent(self.name, self.doctype)
		return agent.ping()

	@frappe.whitelist()
	def ping_agent_job(self):
		agent = Agent(self.name, self.doctype)
		return agent.create_agent_job("Ping Job", "ping_job").name

	@frappe.whitelist()
	def update_agent(self):
		agent = Agent(self.name, self.doctype)
		return agent.update()

	@frappe.whitelist()
	def prepare_server(self):
		if self.provider == "Generic":
			self._prepare_server()
		else:
			frappe.enqueue_doc(self.doctype, self.name, "_prepare_server", queue="long", timeout=2400)

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
			if self.provider != "Generic":
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
		frappe.enqueue_doc(self.doctype, self.name, "_setup_server", queue="long", timeout=2400)

	@frappe.whitelist()
	def install_nginx(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_install_nginx", queue="long", timeout=1200)

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
		frappe.enqueue_doc(self.doctype, self.name, "_install_filebeat", queue="long", timeout=1200)

	def _install_filebeat(self):
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password("kibana_password")
		else:
			kibana_password = None

		try:
			ansible = Ansible(
				playbook="filebeat.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server_type": self.doctype,
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
		frappe.enqueue_doc(self.doctype, self.name, "_install_exporters", queue="long", timeout=1200)

	@frappe.whitelist()
	def ping_ansible(self):
		try:
			ansible = Ansible(
				playbook="ping.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
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
				variables={
					"agent_repository_url": self.get_agent_repository_url(),
					"agent_repository_branch": self.get_agent_repository_branch(),
				},
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
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
			if self.provider == "Scaleway" or self.provider in ("AWS EC2", "OCI"):
				ansible = Ansible(
					playbook="ping.yml",
					server=self,
					user="ubuntu",
				)
			ansible.run()
		except Exception:
			log_error("Unprepared Server Ping Exception", server=self.as_dict())

	@frappe.whitelist()
	def cleanup_unused_files(self):
		if self.is_build_server():
			return

		frappe.enqueue_doc(self.doctype, self.name, "_cleanup_unused_files", queue="long", timeout=2400)

	def is_build_server(self) -> bool:
		# Not a field in all subclasses
		if getattr(self, "use_for_build", False):
			return True

		name = frappe.db.get_single_value("Press Settings", "build_server")
		if name == self.name:
			return True

		# Whether build_server explicitly set on Release Group
		count = frappe.db.count(
			"Release Group",
			{
				"enabled": True,
				"build_server": self.name,
			},
		)
		if isinstance(count, (int, float)):
			return count > 0
		return False

	def _cleanup_unused_files(self):
		agent = Agent(self.name, self.doctype)
		if agent.should_skip_requests():
			return
		agent.cleanup_unused_files()

	def on_trash(self):
		plays = frappe.get_all("Ansible Play", filters={"server": self.name})
		for play in plays:
			frappe.delete_doc("Ansible Play", play.name)

	def break_glass(self):
		"""
		Remove glass file with simple ssh command to make free space

		Space is required for playbooks to run, growpart command, etc.
		"""
		try:
			subprocess.check_output(
				shlex.split(
					f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@{self.ip} -t rm /root/glass"
				),
				stderr=subprocess.STDOUT,
			)
		except subprocess.CalledProcessError as e:
			log_error(f"Error removing glassfile: {e.output.decode()}")

	@frappe.whitelist()
	def extend_ec2_volume(self, device=None):
		if self.provider not in ("AWS EC2", "OCI"):
			return
		# Restart MariaDB if MariaDB disk is full
		mountpoint = self.guess_data_disk_mountpoint()
		restart_mariadb = self.doctype == "Database Server" and self.is_disk_full(
			mountpoint
		)  # check before breaking glass to ensure state of mariadb
		self.break_glass()
		if not device:
			# Try the best guess. Try extending the data volume
			volume = self.find_mountpoint_volume(mountpoint)
			device = self.get_device_from_volume_id(volume.volume_id)
		try:
			ansible = Ansible(
				playbook="extend_ec2_volume.yml",
				server=self,
				variables={"restart_mariadb": restart_mariadb, "device": device},
			)
			ansible.run()
		except Exception:
			log_error("EC2 Volume Extend Exception", server=self.as_dict())

	def enqueue_extend_ec2_volume(self, device):
		frappe.enqueue_doc(self.doctype, self.name, "extend_ec2_volume", device=device)

	@cached_property
	def time_to_wait_before_updating_volume(self) -> timedelta | int:
		if self.provider != "AWS EC2":
			return 0
		if not (
			last_updated_at := frappe.get_value(
				"Virtual Machine Volume",
				{"parent": self.virtual_machine, "idx": 1},  # first volume is likely main
				"last_updated_at",
			)
		):
			return 0
		diff = frappe.utils.now_datetime() - last_updated_at
		return diff if diff < timedelta(hours=6) else 0

	@frappe.whitelist()
	def increase_disk_size(self, increment=50, mountpoint=None):
		if self.provider not in ("AWS EC2", "OCI"):
			return
		if self.provider == "AWS EC2" and self.time_to_wait_before_updating_volume:
			frappe.throw(
				f"Please wait {fmt_timedelta(self.time_to_wait_before_updating_volume)} before resizing volume",
				VolumeResizeLimitError,
			)
		if not mountpoint:
			mountpoint = self.guess_data_disk_mountpoint()

		volume = self.find_mountpoint_volume(mountpoint)

		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", self.virtual_machine)
		virtual_machine.increase_disk_size(volume.volume_id, increment)
		if self.provider == "AWS EC2":
			device = self.get_device_from_volume_id(volume.volume_id)
			self.enqueue_extend_ec2_volume(device)
		elif self.provider == "OCI":
			# TODO: Add support for volumes on OCI
			# Non-boot volumes might not need resize
			self.break_glass()
			self.reboot()

	def guess_data_disk_mountpoint(self) -> str:
		if not self.has_data_volume:
			return "/"

		volumes = self.get_volume_mounts()
		if volumes:
			if self.doctype == "Server":
				mountpoint = "/opt/volumes/benches"
			elif self.doctype == "Database Server":
				mountpoint = "/opt/volumes/mariadb"
		else:
			mountpoint = "/"
		return mountpoint

	def find_mountpoint_volume(self, mountpoint):
		machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", self.virtual_machine)

		if len(machine.volumes) == 1:
			# If there is only one volume,
			# then all mountpoints are on the same volume
			return machine.volumes[0]

		volumes = self.get_volume_mounts()
		volume = find(volumes, lambda x: x.mount_point == mountpoint)
		if volume:
			# If the volume is in `mounts`, that means it's a data volume
			return volume
		# Otherwise it's a root volume
		return find(machine.volumes, lambda v: v.device == "/dev/sda1")

	def update_virtual_machine_name(self):
		if self.provider not in ("AWS EC2", "OCI"):
			return None
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
			{
				"document_type": self.doctype,
				"document_name": self.name,
				"team": self.team,
				"plan_type": "Server Plan",
			},
		)
		return frappe.get_doc("Subscription", name) if name else None

	@property
	def add_on_storage_subscription(self):
		name = frappe.db.get_value(
			"Subscription",
			{
				"document_type": self.doctype,
				"document_name": self.name,
				"team": self.team,
				"plan_type": "Server Storage Plan",
			},
		)
		return frappe.get_doc("Subscription", name) if name else None

	def create_subscription_for_storage(self, increment: int) -> None:
		plan_type = "Server Storage Plan"
		plan = frappe.get_value(plan_type, {"enabled": 1}, "name")

		if existing_subscription := frappe.db.get_value(
			"Subscription",
			{
				"document_type": self.doctype,
				"document_name": self.name,
				"team": self.team,
				"plan_type": plan_type,
				"plan": plan,
			},
			["name", "additional_storage"],
			as_dict=True,
		):
			frappe.db.set_value(
				"Subscription",
				existing_subscription.name,
				"additional_storage",
				increment + cint(existing_subscription.additional_storage),
			)
		else:
			frappe.get_doc(
				{
					"doctype": "Subscription",
					"document_type": self.doctype,
					"document_name": self.name,
					"team": self.team,
					"plan_type": plan_type,
					"plan": plan,
					"additional_storage": increment,
				}
			).insert()

	@frappe.whitelist()
	def rename_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_rename_server", queue="long", timeout=2400)

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
				frappe.db.set_value("Self Hosted Server", {"server": self.name}, "status", "Archived")

		else:
			frappe.enqueue_doc(self.doctype, self.name, "_archive", queue="long")
		self.disable_subscription()

		frappe.db.delete("Press Role Permission", {"server": self.name})

	def _archive(self):
		self.run_press_job("Archive Server")

	def disable_subscription(self):
		subscription = self.subscription
		if subscription:
			subscription.disable()

		# disable add-on storage subscription
		add_on_storage_subscription = self.add_on_storage_subscription
		if add_on_storage_subscription:
			add_on_storage_subscription.disable()

	def can_change_plan(self, ignore_card_setup):
		if is_system_user(frappe.session.user):
			return

		if ignore_card_setup:
			return

		team = frappe.get_doc("Team", self.team)

		if team.parent_team:
			team = frappe.get_doc("Team", team.parent_team)

		if team.payment_mode == "Paid By Partner" and team.billing_team:
			team = frappe.get_doc("Team", team.billing_team)

		if team.is_defaulter():
			frappe.throw("Cannot change plan because you have unpaid invoices")

		if not (team.default_payment_method or team.get_balance()):
			frappe.throw("Cannot change plan because you haven't added a card and not have enough balance")

	@dashboard_whitelist()
	def change_plan(self, plan, ignore_card_setup=False):
		self.can_change_plan(ignore_card_setup)
		plan = frappe.get_doc("Server Plan", plan)
		self._change_plan(plan)
		self.run_press_job("Resize Server", {"machine_type": plan.instance_type})

	def _change_plan(self, plan):
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

		if not certificate_name and self.is_self_hosted:
			certificate_name = frappe.db.get_value("TLS Certificate", {"domain": f"{self.name}"}, "name")

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
			kibana_password = frappe.get_doc("Log Server", log_server).get_password("kibana_password")
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
			"increase_swap_locked",
			queue="long",
			timeout=1200,
			**{"swap_size": swap_size},
		)

	def _increase_swap(self, swap_size=4):
		"""Increase swap by size defined"""
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
			log_error("Increase swap exception", doc=self)

	def increase_swap_locked(self, swap_size=4):
		with filelock(f"{self.name}-swap-update"):
			self._increase_swap(swap_size)

	@frappe.whitelist()
	def reset_swap(self, swap_size=1):
		"""
		Replace existing swap files with new swap file of given size
		"""
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"reset_swap_locked",
			queue="long",
			timeout=1200,
			**{"swap_size": swap_size},
		)

	def reset_swap_locked(self, swap_size=1):
		with filelock(f"{self.name}-swap-update"):
			self._reset_swap(swap_size)

	def _reset_swap(self, swap_size=1):
		"""Reset swap by removing existing swap files and creating new swap"""
		# list of swap files to remove assuming minimum swap size of 1 GB to be safe. Wrong names are handled in playbook
		swap_files_to_remove = ["swap.default", "swap"]
		swap_files_to_remove += ["swap" + str(i) for i in range(1, 30)]
		try:
			ansible = Ansible(
				playbook="reset_swap.yml",
				server=self,
				variables={
					"swap_size": swap_size,
					"swap_file": "swap",
					"swap_files_to_remove": swap_files_to_remove,
				},
			)
			ansible.run()
		except Exception:
			log_error("Reset swap exception", doc=self)

	def add_glass_file(self):
		frappe.enqueue_doc(self.doctype, self.name, "_add_glass_file")

	def _add_glass_file(self):
		try:
			ansible = Ansible(playbook="glass_file.yml", server=self)
			ansible.run()
		except Exception:
			log_error("Add Glass File Exception", doc=self)

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
			log_error("MySQLdump Setup Exception", doc=self)

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
			log_error("Swappiness Setup Exception", doc=self)

	def update_filebeat(self):
		frappe.enqueue_doc(self.doctype, self.name, "_update_filebeat")

	def _update_filebeat(self):
		try:
			ansible = Ansible(
				playbook="filebeat_update.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Filebeat Update Exception", doc=self)

	@frappe.whitelist()
	def update_tls_certificate(self):
		from press.press.doctype.tls_certificate.tls_certificate import (
			update_server_tls_certifcate,
		)

		filters = {"wildcard": True, "status": "Active", "domain": self.domain}

		if (
			hasattr(self, "is_self_hosted")
			and self.is_self_hosted
			and self.domain != self.self_hosted_server_domain
		):
			filters["domain"] = self.name
			del filters["wildcard"]

		certificate = frappe.get_last_doc("TLS Certificate", filters)

		update_server_tls_certifcate(self, certificate)

	@frappe.whitelist()
	def show_agent_version(self) -> str:
		return self.agent.get_version()["commit"]

	@frappe.whitelist()
	def show_agent_password(self) -> str:
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
		if self.provider != "AWS EC2":
			raise NotImplementedError
		console = frappe.new_doc("Serial Console Log")
		console.server_type = self.doctype
		console.server = self.name
		console.virtual_machine = self.virtual_machine
		console.action = "reboot"
		console.save()
		console.reload()
		console.run_sysrq()

	@dashboard_whitelist()
	def reboot(self):
		if self.provider in ("AWS EC2", "OCI"):
			virtual_machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
			virtual_machine.reboot()

	@dashboard_whitelist()
	def rename(self, title):
		self.title = title
		self.save()

	def validate_mounts(self):
		if not self.virtual_machine:
			return
		machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		if machine.has_data_volume and len(machine.volumes) > 1 and not self.mounts:
			self.fetch_volumes_from_virtual_machine()
			self.set_default_mount_points()
			self.set_mount_properties()

	def fetch_volumes_from_virtual_machine(self):
		machine = frappe.get_doc("Virtual Machine", self.virtual_machine)
		for volume in machine.volumes:
			if volume.device == "/dev/sda1":
				# Skip root volume. This is for AWS other providers may have different root volume
				continue
			self.append("mounts", {"volume_id": volume.volume_id})

	def set_default_mount_points(self):
		first = self.mounts[0]
		if self.doctype == "Server":
			first.mount_point = "/opt/volumes/benches"
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/home/frappe/benches",
					"source": "/opt/volumes/benches/home/frappe/benches",
					"mount_point_owner": "frappe",
					"mount_point_group": "frappe",
				},
			)
		elif self.doctype == "Database Server":
			first.mount_point = "/opt/volumes/mariadb"
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/var/lib/mysql",
					"source": "/opt/volumes/mariadb/var/lib/mysql",
				},
			)
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/etc/mysql",
					"source": "/opt/volumes/mariadb/etc/mysql",
				},
			)

	def set_mount_properties(self):
		for mount in self.mounts:
			# set_defaults doesn't seem to work on children in a controller hook
			default_fields = find_all(frappe.get_meta("Server Mount").fields, lambda x: x.default)
			for field in default_fields:
				fieldname = field.fieldname
				if not mount.get(fieldname):
					mount.set(fieldname, field.default)

			mount_options = "defaults,nofail"  # Set default mount options
			if mount.mount_options:
				mount_options = f"{mount_options},{mount.mount_options}"

			mount.mount_options = mount_options
			if mount.mount_type == "Bind":
				mount.filesystem = "none"
				mount.mount_options = f"{mount.mount_options},bind"

			if mount.volume_id:
				# EBS volumes are named by their volume id
				# There's likely a better way to do this
				# https://docs.aws.amazon.com/ebs/latest/userguide/ebs-using-volumes.html
				stripped_id = mount.volume_id.replace("-", "")
				mount.source = self.get_device_from_volume_id(mount.volume_id)
				if not mount.mount_point:
					# If we don't know where to mount, mount it in /mnt/<volume_id>
					mount.mount_point = f"/mnt/{stripped_id}"

	def get_device_from_volume_id(self, volume_id):
		stripped_id = volume_id.replace("-", "")
		return f"/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_{stripped_id}"

	def get_mount_variables(self):
		return {
			"all_mounts_json": json.dumps([mount.as_dict() for mount in self.mounts], indent=4, default=str),
			"volume_mounts_json": json.dumps(
				self.get_volume_mounts(),
				indent=4,
				default=str,
			),
			"bind_mounts_json": json.dumps(
				[mount.as_dict() for mount in self.mounts if mount.mount_type == "Bind"],
				indent=4,
				default=str,
			),
		}

	def get_volume_mounts(self):
		return [mount.as_dict() for mount in self.mounts if mount.mount_type == "Volume"]

	@frappe.whitelist()
	def mount_volumes(self):
		frappe.enqueue_doc(self.doctype, self.name, "_mount_volumes", queue="short", timeout=1200)

	def _mount_volumes(self):
		try:
			ansible = Ansible(
				playbook="mount.yml",
				server=self,
				variables={**self.get_mount_variables()},
			)
			play = ansible.run()
			self.reload()
			if self._set_mount_status(play):
				self.save()
		except Exception:
			log_error("Server Mount Exception", server=self.as_dict())

	def _set_mount_status(self, play):
		tasks = frappe.get_all(
			"Ansible Task",
			["result", "task"],
			{
				"play": play.name,
				"status": ("in", ("Success", "Failure")),
				"task": ("in", ("Mount Volumes", "Mount Bind Mounts", "Show Block Device UUIDs")),
			},
		)
		mounts_changed = False
		for task in tasks:
			result = json.loads(task.result)
			for row in result.get("results", []):
				mount = find(self.mounts, lambda x: x.name == row.get("item", {}).get("name"))
				if not mount:
					mount = find(
						self.mounts, lambda x: x.name == row.get("item", {}).get("item", {}).get("name")
					)
				if not mount:
					continue
				if task.task == "Show Block Device UUIDs":
					mount.uuid = row.get("stdout", "").strip()
					mounts_changed = True
				else:
					mount_status = {True: "Failure", False: "Success"}[row.get("failed", False)]
					if mount.status != mount_status:
						mount.status = mount_status
						mounts_changed = True
		return mounts_changed

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

	def free_space(self, mountpoint: str) -> int:
		from press.api.server import prometheus_query

		response = prometheus_query(
			f"""node_filesystem_avail_bytes{{instance="{self.name}", job="node", mountpoint="{mountpoint}"}}""",
			lambda x: x["mountpoint"],
			"Asia/Kolkata",
			60,
			60,
		)["datasets"]
		if response:
			return response[0]["values"][-1]
		return 50 * 1024 * 1024 * 1024  # Assume 50GB free space

	def is_disk_full(self, mountpoint: str) -> bool:
		return self.free_space(mountpoint) == 0

	def space_available_in_6_hours(self, mountpoint: str) -> int:
		from press.api.server import prometheus_query

		response = prometheus_query(
			f"""predict_linear(
node_filesystem_avail_bytes{{instance="{self.name}", mountpoint="{mountpoint}"}}[3h], 6*3600
			)""",
			lambda x: x["mountpoint"],
			"Asia/Kolkata",
			120,
			120,
		)["datasets"]
		if not response:
			return -20 * 1024 * 1024 * 1024
		return response[0]["values"][-1]

	def disk_capacity(self, mountpoint: str) -> int:
		from press.api.server import prometheus_query

		response = prometheus_query(
			f"""node_filesystem_size_bytes{{instance="{self.name}", job="node", mountpoint="{mountpoint}"}}""",
			lambda x: x["mountpoint"],
			"Asia/Kolkata",
			120,
			120,
		)["datasets"]
		if response:
			return response[0]["values"][-1]
		return frappe.db.get_value("Virtual Machine", self.virtual_machine, "disk_size") * 1024 * 1024 * 1024

	def size_to_increase_by_for_20_percent_available(self, mountpoint: str):  # min 50 GB, max 250 GB
		return int(
			min(
				self.auto_add_storage_max,
				max(
					self.auto_add_storage_min,
					abs(self.disk_capacity(mountpoint) - self.space_available_in_6_hours(mountpoint) * 5)
					/ 4
					/ 1024
					/ 1024
					/ 1024,
				),
			)
		)

	def calculated_increase_disk_size(
		self,
		additional: int = 0,
		mountpoint: str | None = None,
	):
		telegram = Telegram("Information")
		buffer = self.size_to_increase_by_for_20_percent_available(mountpoint)
		telegram.send(
			f"Increasing disk (mount point {mountpoint})on [{self.name}]({frappe.utils.get_url_to_form(self.doctype, self.name)}) by {buffer + additional}G"
		)
		self.increase_disk_size_for_server(self.name, buffer + additional, mountpoint)

	def prune_docker_system(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_prune_docker_system",
			queue="long",
			timeout=8000,
		)

	def _prune_docker_system(self):
		try:
			ansible = Ansible(
				playbook="docker_system_prune.yml",
				server=self,
			)
			ansible.run()
		except Exception:
			log_error("Prune Docker System Exception", doc=self)

	def reload_nginx(self):
		agent = Agent(self.name, server_type=self.doctype)
		agent.reload_nginx()

	def _ssh_user(self):
		if not hasattr(self, "ssh_user"):
			return "root"
		return self.ssh_user or "root"

	def _ssh_port(self):
		if not hasattr(self, "ssh_port"):
			return 22
		return self.ssh_port or 22

	def get_primary_frappe_public_key(self):
		if primary_public_key := frappe.db.get_value(self.doctype, self.primary, "frappe_public_key"):
			return primary_public_key

		primary = frappe.get_doc(self.doctype, self.primary)
		ansible = Ansible(
			playbook="fetch_frappe_public_key.yml",
			server=primary,
		)
		play = ansible.run()
		if play.status == "Success":
			return frappe.db.get_value(self.doctype, self.primary, "frappe_public_key")
		frappe.throw(f"Failed to fetch {primary.name}'s Frappe public key")
		return None

	def copy_files(self, source, destination):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_copy_files",
			source=source,
			destination=destination,
			queue="long",
			timeout=7200,
		)

	def _copy_files(self, source, destination):
		try:
			ansible = Ansible(
				playbook="copy.yml",
				server=self,
				variables={
					"source": source,
					"destination": destination,
				},
			)
			ansible.run()
		except Exception:
			log_error("Sever File Copy Exception", server=self.as_dict())


class Server(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.resource_tag.resource_tag import ResourceTag
		from press.press.doctype.server_mount.server_mount import ServerMount

		agent_password: DF.Password | None
		auto_add_storage_max: DF.Int
		auto_add_storage_min: DF.Int
		cluster: DF.Link | None
		database_server: DF.Link | None
		disable_agent_job_auto_retry: DF.Check
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		has_data_volume: DF.Check
		hostname: DF.Data
		hostname_abbreviation: DF.Data | None
		ignore_incidents_since: DF.Datetime | None
		ip: DF.Data | None
		ipv6: DF.Data | None
		is_managed_database: DF.Check
		is_primary: DF.Check
		is_pyspy_setup: DF.Check
		is_replication_setup: DF.Check
		is_self_hosted: DF.Check
		is_server_prepared: DF.Check
		is_server_renamed: DF.Check
		is_server_setup: DF.Check
		is_standalone: DF.Check
		is_standalone_setup: DF.Check
		is_upstream_setup: DF.Check
		managed_database_service: DF.Link | None
		mounts: DF.Table[ServerMount]
		new_worker_allocation: DF.Check
		plan: DF.Link | None
		primary: DF.Link | None
		private_ip: DF.Data | None
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		proxy_server: DF.Link | None
		public: DF.Check
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
		use_agent_job_callbacks: DF.Check
		use_for_build: DF.Check
		use_for_new_benches: DF.Check
		use_for_new_sites: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	GUNICORN_MEMORY = 150  # avg ram usage of 1 gunicorn worker
	BACKGROUND_JOB_MEMORY = 3 * 80  # avg ram usage of 3 sets of bg workers

	def on_update(self):
		# If Database Server is changed for the server then change it for all the benches
		if not self.is_new() and (
			self.has_value_changed("database_server") or self.has_value_changed("managed_database_service")
		):
			benches = frappe.get_all("Bench", {"server": self.name, "status": ("!=", "Archived")})
			for bench in benches:
				bench = frappe.get_doc("Bench", bench)
				bench.database_server = self.database_server
				bench.managed_database_service = self.managed_database_service
				bench.save()

		if self.database_server:
			database_server_public = frappe.db.get_value("Database Server", self.database_server, "public")
			if database_server_public != self.public:
				frappe.db.set_value("Database Server", self.database_server, "public", self.public)

		if not self.is_new() and self.has_value_changed("team"):
			self.update_subscription()
			frappe.db.delete("Press Role Permission", {"server": self.name})

		# Enable bench memory limits for public servers
		if self.public:
			self.set_bench_memory_limits = True

	def after_insert(self):
		from press.press.doctype.press_role.press_role import (
			add_permission_for_newly_created_doc,
		)

		super().after_insert()
		add_permission_for_newly_created_doc(self)

	def update_subscription(self):
		subscription = frappe.db.get_value(
			"Subscription",
			{
				"document_type": self.doctype,
				"document_name": self.name,
				"plan_type": "Server Plan",
				"plan": self.plan,
				"enabled": 1,
			},
			["name", "team"],
			as_dict=True,
		)
		if subscription and subscription.team != self.team:
			frappe.get_doc("Subscription", subscription).disable()

			if subscription := frappe.db.get_value(
				"Subscription",
				{
					"document_type": self.doctype,
					"document_name": self.name,
					"team": self.team,
					"plan_type": "Server Plan",
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
							"plan_type": "Server Plan",
							"plan": self.plan,
						}
					).insert()
				except Exception:
					frappe.log_error("Server Subscription Creation Error")

		add_on_storage_subscription = frappe.db.get_value(
			"Subscription",
			{
				"document_type": self.doctype,
				"document_name": self.name,
				"plan_type": "Server Storage Plan",
				"enabled": 1,
			},
			["name", "team", "additional_storage"],
			as_dict=True,
		)
		if add_on_storage_subscription and add_on_storage_subscription.team != self.team:
			frappe.get_doc("Subscription", add_on_storage_subscription).disable()

			if existing_add_on_storage_subscription := frappe.db.get_value(
				"Subscription",
				filters={
					"document_type": self.doctype,
					"document_name": self.name,
					"team": self.team,
					"plan_type": "Server Storage Plan",
				},
			):
				frappe.db.set_value(
					"Subscription",
					existing_add_on_storage_subscription,
					{
						"enabled": 1,
						"additional_storage": add_on_storage_subscription.additional_storage,
					},
				)
			else:
				try:
					# create new subscription
					frappe.get_doc(
						{
							"doctype": "Subscription",
							"document_type": self.doctype,
							"document_name": self.name,
							"team": self.team,
							"plan_type": "Server Storage Plan",
							"plan": add_on_storage_subscription.plan,
						}
					).insert()
				except Exception:
					frappe.log_error("Server Storage Subscription Creation Error")

	@frappe.whitelist()
	def add_upstream_to_proxy(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_server(self.name)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		certificate = self.get_certificate()
		log_server, kibana_password = self.get_log_server()
		agent_sentry_dsn = frappe.db.get_single_value("Press Settings", "agent_sentry_dsn")

		try:
			ansible = Ansible(
				playbook="self_hosted.yml" if getattr(self, "is_self_hosted", False) else "server.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"proxy_ip": self.get_proxy_ip(),
					"workers": "2",
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"agent_sentry_dsn": agent_sentry_dsn,
					"monitoring_password": self.get_monitoring_password(),
					"log_server": log_server,
					"kibana_password": kibana_password,
					"certificate_private_key": certificate.private_key,
					"certificate_full_chain": certificate.full_chain,
					"certificate_intermediate_chain": certificate.intermediate_chain,
					"docker_depends_on_mounts": self.docker_depends_on_mounts,
					**self.get_mount_variables(),
				},
			)
			play = ansible.run()
			self.reload()
			self._set_mount_status(play)
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Server Setup Exception", server=self.as_dict())
		self.save()

	def get_proxy_ip(self):
		"""In case of standalone setup proxy will not required"""

		if self.is_standalone:
			return self.ip

		return frappe.db.get_value("Proxy Server", self.proxy_server, "private_ip")

	@frappe.whitelist()
	def setup_standalone(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_standalone", queue="short", timeout=1200)

	def _setup_standalone(self):
		try:
			ansible = Ansible(
				playbook="standalone.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
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
	def setup_agent_sentry(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_agent_sentry")

	def _setup_agent_sentry(self):
		agent_sentry_dsn = frappe.db.get_single_value("Press Settings", "agent_sentry_dsn")
		try:
			ansible = Ansible(
				playbook="agent_sentry.yml",
				server=self,
				variables={"agent_sentry_dsn": agent_sentry_dsn},
			)
			ansible.run()
		except Exception:
			log_error("Agent Sentry Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def whitelist_ipaddress(self):
		frappe.enqueue_doc(self.doctype, self.name, "_whitelist_ip", queue="short", timeout=1200)

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
		frappe.enqueue_doc(self.doctype, self.name, "_agent_set_proxy_ip", queue="short", timeout=1200)

	def _agent_set_proxy_ip(self):
		agent_password = self.get_password("agent_password")

		try:
			ansible = Ansible(
				playbook="agent_set_proxy_ip.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"proxy_ip": self.get_proxy_ip(),
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
		frappe.enqueue_doc(self.doctype, self.name, "_setup_fail2ban", queue="long", timeout=1200)

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
	def setup_pyspy(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_pyspy", queue="long")

	def _setup_pyspy(self):
		try:
			ansible = Ansible(
				playbook="setup_pyspy.yml", server=self, user=self._ssh_user(), port=self._ssh_port()
			)
			play: AnsiblePlay = ansible.run()
			self.is_pyspy_setup = play.status == "Success"
			self.save()
		except Exception:
			log_error("Setup PySpy Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_replication(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_setup_replication", queue="long", timeout=1200)

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
		try:
			ansible = Ansible(
				playbook="secondary_app.yml",
				server=self,
				variables={"primary_public_key": self.get_primary_frappe_public_key()},
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
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password("monitoring_password")
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
	def get_all_prod(cls, **kwargs) -> list[str]:
		"""Active prod servers."""
		return frappe.get_all("Server", {"status": "Active"}, pluck="name", **kwargs)

	@classmethod
	def get_all_primary_prod(cls) -> list[str]:
		"""Active primary prod servers."""
		return frappe.get_all("Server", {"status": "Active", "is_primary": True}, pluck="name")

	@classmethod
	def get_all_staging(cls, **kwargs) -> list[str]:
		"""Active staging servers."""
		return frappe.get_all("Server", {"status": "Active", "staging": True}, pluck="name", **kwargs)

	@classmethod
	def get_one_staging(cls) -> str:
		return cls.get_all_staging(limit=1)[0]

	@classmethod
	def get_prod_for_new_bench(cls, extra_filters=None) -> str | None:
		filters = {"status": "Active", "use_for_new_benches": True}
		if extra_filters:
			filters.update(extra_filters)
		servers = frappe.get_all("Server", {**filters}, pluck="name", limit=1)
		if servers:
			return servers[0]
		return None

	def _rename_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password("monitoring_password")
		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password("kibana_password")
		else:
			kibana_password = None

		try:
			ansible = Ansible(
				playbook="rename.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"private_ip": self.private_ip,
					"proxy_ip": self.get_proxy_ip(),
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
			bench = frappe.get_doc("Bench", bench_name)
			bench_workloads[bench] = bench.workload
		return bench_workloads

	@cached_property
	def workload(self) -> int:
		return sum(self.bench_workloads.values())

	@cached_property
	def usable_ram(self) -> float:
		return max(self.ram - 3000, self.ram * 0.75)  # in MB (leaving some for disk cache + others)

	@cached_property
	def max_gunicorn_workers(self) -> int:
		usable_ram_for_gunicorn = 0.6 * self.usable_ram  # 60% of usable ram
		return usable_ram_for_gunicorn / self.GUNICORN_MEMORY

	@cached_property
	def max_bg_workers(self) -> int:
		usable_ram_for_bg = 0.4 * self.usable_ram  # 40% of usable ram
		return usable_ram_for_bg / self.BACKGROUND_JOB_MEMORY

	def _auto_scale_workers_new(self, commit):
		for bench in self.bench_workloads:
			try:
				bench.reload()
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
			except frappe.TimestampMismatchError:
				if commit:
					frappe.db.rollback()
				continue
			except Exception:
				log_error("Bench Auto Scale Worker Error", bench=bench, workload=self.bench_workloads[bench])
				if commit:
					frappe.db.rollback()

	def _auto_scale_workers_old(self):  # noqa: C901
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
	def docker_depends_on_mounts(self):
		mount_points = set(mount.mount_point for mount in self.mounts)
		bench_mount_points = set(["/home/frappe/benches"])
		return bench_mount_points.issubset(mount_points)


def scale_workers(now=False):
	servers = frappe.get_all("Server", {"status": "Active", "is_primary": True})
	for server in servers:
		try:
			if now:
				frappe.get_doc("Server", server.name).auto_scale_workers()
			else:
				frappe.enqueue_doc(
					"Server",
					server.name,
					method="auto_scale_workers",
					job_id=f"auto_scale_workers:{server.name}",
					deduplicate=True,
					queue="long",
					enqueue_after_commit=True,
				)
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
	is_public = frappe.db.get_value("Server", server_name, "public")
	return not is_public
