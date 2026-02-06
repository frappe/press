# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import datetime
import ipaddress
import json
import shlex
import typing
from contextlib import suppress
from datetime import timedelta
from functools import cached_property

import boto3
import frappe
import semantic_version
from frappe import _
from frappe.core.utils import find, find_all
from frappe.installer import subprocess
from frappe.model.document import Document
from frappe.utils.password import get_decrypted_password
from frappe.utils.synchronization import filelock
from frappe.utils.user import is_system_user

from press.agent import Agent
from press.api.client import dashboard_whitelist
from press.exceptions import VolumeResizeLimitError
from press.guards import role_guard
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.add_on_storage_log.add_on_storage_log import (
	insert_addon_storage_log,
)
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.press.doctype.auto_scale_record.auto_scale_record import (
	create_prometheus_rule_for_scaling,
	is_secondary_ready_for_scale_down,
	update_or_delete_prometheus_rule_for_scaling,
)
from press.press.doctype.communication_info.communication_info import get_communication_info
from press.press.doctype.resource_tag.tag_helpers import TagHelpers
from press.press.doctype.server_activity.server_activity import log_server_activity
from press.press.doctype.telegram_message.telegram_message import TelegramMessage
from press.runner import Ansible
from press.utils import fmt_timedelta, log_error

if typing.TYPE_CHECKING:
	from press.infrastructure.doctype.arm_build_record.arm_build_record import ARMBuildRecord
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.ansible_play.ansible_play import AnsiblePlay
	from press.press.doctype.auto_scale_record.auto_scale_record import AutoScaleRecord
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.cluster.cluster import Cluster
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.mariadb_variable.mariadb_variable import MariaDBVariable
	from press.press.doctype.nfs_volume_detachment.nfs_volume_detachment import NFSVolumeDetachment
	from press.press.doctype.press_job.press_job import PressJob
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.press.doctype.server_mount.server_mount import ServerMount
	from press.press.doctype.server_plan.server_plan import ServerPlan
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine
	from press.press.doctype.virtual_machine_volume.virtual_machine_volume import VirtualMachineVolume


from typing import Literal, TypedDict


class BenchInfoType(TypedDict):
	name: str
	build: str
	candidate: str


class ARMDockerImageType(TypedDict):
	build: str | None
	status: Literal["Pending", "Preparing", "Running", "Failure", "Success"]
	bench: str


class AutoScaleTriggerRow(TypedDict):
	metric: Literal["CPU", "Memory"]
	action: Literal["Scale Up", "Scale Down"]


PUBLIC_SERVER_AUTO_ADD_STORAGE_MIN = 50
MARIADB_DATA_MNT_POINT = "/opt/volumes/mariadb"
BENCH_DATA_MNT_POINT = "/opt/volumes/benches"


class BaseServer(Document, TagHelpers):
	dashboard_fields = (
		"title",
		"plan",
		"cluster",
		"provider",
		"status",
		"team",
		"database_server",
		"is_self_hosted",
		"auto_add_storage_min",
		"auto_add_storage_max",
		"auto_increase_storage",
		"is_monitoring_disabled",
		"auto_purge_binlog_based_on_size",
		"binlog_max_disk_usage_percent",
		"is_monitoring_disabled",
		"is_provisioning_press_job_completed",
		"is_unified_server",
	)

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		Server = frappe.qb.DocType("Server")

		status = filters.get("status")
		if status == "Archived":
			query = query.where(Server.status == status)
		else:
			# Show only Active and Installing servers ignore pending (secondary server)
			query = query.where(
				Server.status.isin(["Active", "Installing", "Broken"])
				| ((Server.status == "Pending") & (Server.is_secondary != 1))
			)

		query = query.where(Server.is_for_recovery != 1).where(Server.team == frappe.local.team().name)
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

	@property
	def _series(self):
		return self.name[0]

	def create_log(self, action: str, reason: str):
		"""Helper to log server activity"""
		log_server_activity(self._series, self.name, action, reason)

	def get_doc(self, doc):  # noqa: C901
		from press.api.client import get
		from press.api.server import usage

		warn_at_storage_percentage = 0.8

		if doc.status in ("Active", "Pending") and not doc.is_provisioning_press_job_completed:
			doc.status = "Installing"

		if doc.database_server:
			data = frappe.get_value(
				"Database Server",
				doc.database_server,
				["status", "is_provisioning_press_job_completed"],
				as_dict=True,
			)
			if data and data.status in ("Active", "Pending") and not data.is_provisioning_press_job_completed:
				doc.status = "Installing"

		if self.plan:
			doc.current_plan = get("Server Plan", self.plan)
			if doc.current_plan and not doc.current_plan.get("plan_type"):
				doc.current_plan["plan_type"] = frappe.db.get_single_value(
					"Press Settings", "default_server_plan_type"
				)
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

		if not self.is_self_hosted:
			doc.disk_size = self.get_data_disk_size()

		doc.communication_infos = self.get_communication_infos()

		try:
			doc.recommended_storage_increment = (
				self.size_to_increase_by_for_20_percent_available(
					mountpoint=self.guess_data_disk_mountpoint()
				)
				if (doc.usage.get("disk", 0) >= warn_at_storage_percentage * doc.disk_size)
				else 0
			)
		except TypeError:
			doc.recommended_storage_increment = 0

		doc.replication_server = frappe.db.get_value(
			"Database Server",
			{"primary": doc.database_server, "is_replication_setup": 1},
			"name",
		)
		doc.owner_email = frappe.db.get_value("Team", self.team, "user")

		if self.doctype == "Server":
			doc.secondary_server = self.secondary_server
			doc.scaled_up = self.scaled_up

		return doc

	@dashboard_whitelist()
	def get_communication_infos(self):
		return (
			[{"channel": c.channel, "type": c.type, "value": c.value} for c in self.communication_infos]
			if hasattr(self, "communication_infos")
			else []
		)

	@dashboard_whitelist()
	def update_communication_infos(self, values: list[dict]):
		if self.doctype != "Server":
			frappe.throw("Setting up communication info is only allowed for App Server")
			return

		from press.press.doctype.communication_info.communication_info import (
			update_communication_infos as update_infos,
		)

		update_infos("Server", self.name, values)

	@dashboard_whitelist()
	def get_storage_usage(self):
		"""Get storage usage of the application server"""
		try:
			return self.agent.get("/server/storage-breakdown")
		except Exception:
			frappe.throw("Failed to fetch storage usage. Try again later.")

	@dashboard_whitelist()
	def increase_disk_size_for_server(
		self,
		server: str | Server | DatabaseServer,
		increment: int,
		mountpoint: str | None = None,
		is_auto_triggered: bool = False,
		current_disk_usage: int | None = None,
	) -> None:
		add_on_storage_log = None
		storage_parameters = {
			"doctype": "Add On Storage Log",
			"adding_storage": increment,
			is_auto_triggered: is_auto_triggered,
		}

		if not isinstance(server, str):
			server = server.name

		storage_parameters.update({"database_server" if server[0] == "m" else "server": server})

		if server == self.name:
			mountpoint = mountpoint or self.guess_data_disk_mountpoint()
			storage_parameters.update(
				{
					"available_disk_space": round((self.disk_capacity(mountpoint) / 1024 / 1024 / 1024), 2),
					"current_disk_usage": current_disk_usage
					or round(
						(self.disk_capacity(mountpoint) - self.free_space(mountpoint)) / 1024 / 1024 / 1024, 2
					),
					"mountpoint": mountpoint,
				}
			)
			if increment:
				add_on_storage_log = insert_addon_storage_log(
					adding_storage=increment,
					available_disk_space=round((self.disk_capacity(mountpoint) / 1024 / 1024 / 1024), 2),
					current_disk_usage=current_disk_usage
					or round(
						(self.disk_capacity(mountpoint) - self.free_space(mountpoint)) / 1024 / 1024 / 1024, 2
					),
					mountpoint=mountpoint,
					is_auto_triggered=is_auto_triggered,
					is_warning=False,
					server=storage_parameters.get("server"),
					database_server=storage_parameters.get("database_server"),
				)

			self.increase_disk_size(
				increment=increment,
				mountpoint=mountpoint,
				log=add_on_storage_log.name if add_on_storage_log else None,
			)
		else:
			server_doc: DatabaseServer = frappe.get_doc("Database Server", server)
			mountpoint = (
				mountpoint or server_doc.guess_data_disk_mountpoint()
			)  # Name will now be changed to m*
			storage_parameters.update(
				{
					"available_disk_space": round((self.disk_capacity(mountpoint) / 1024 / 1024 / 1024), 2),
					"current_disk_usage": current_disk_usage
					or round(
						(self.disk_capacity(mountpoint) - self.free_space(mountpoint)) / 1024 / 1024 / 1024, 2
					),
					"mountpoint": mountpoint,
				}
			)
			if increment:
				add_on_storage_log = insert_addon_storage_log(
					adding_storage=increment,
					available_disk_space=round((self.disk_capacity(mountpoint) / 1024 / 1024 / 1024), 2),
					current_disk_usage=current_disk_usage
					or round(
						(self.disk_capacity(mountpoint) - self.free_space(mountpoint)) / 1024 / 1024 / 1024, 2
					),
					mountpoint=mountpoint,
					is_auto_triggered=is_auto_triggered,
					is_warning=False,
					server=storage_parameters.get("server"),
					database_server=storage_parameters.get("database_server"),
				)

			server_doc.increase_disk_size(
				increment=increment,
				mountpoint=mountpoint,
				log=add_on_storage_log.name if add_on_storage_log else None,
			)

	@dashboard_whitelist()
	def configure_auto_add_storage(self, server: str, enabled: bool, min: int = 0, max: int = 0) -> None:
		if not enabled:
			frappe.db.set_value(self.doctype, self.name, "auto_increase_storage", False)
			return

		if min < 0 or max < 0:
			frappe.throw(_("Minimum and maximum storage sizes must be positive"))
		if min > max:
			frappe.throw(_("Minimum storage size must be less than the maximum storage size"))

		if server == self.name:
			self.auto_increase_storage = True
			self.auto_add_storage_min = min
			self.auto_add_storage_max = max
			self.save()
		else:
			server_doc = frappe.get_doc("Database Server", server)
			server_doc.auto_increase_storage = True
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

	def _get_clusters_with_autoscale_support(self) -> list[str]:
		"""Get clusters which have autoscaling enabled"""
		return frappe.db.get_all("Cluster", {"enable_autoscaling": 1}, pluck="name")

	def get_actions(self):
		server_type = ""
		if self.doctype == "Server":
			server_type = "application server" if not getattr(self, "is_unified_server", False) else "server"
		elif self.doctype == "Database Server":
			if self.is_replication_setup:
				server_type = "replication server"
			else:
				server_type = (
					"database server" if not getattr(self, "is_unified_server", False) else "database"
				)

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
				"condition": self.should_show_reboot(),
				"doc_method": "reboot",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Cleanup Server",
				"description": f"Cleanup unused files on the {server_type}",
				"button_label": "Cleanup",
				"condition": self.status == "Active" and self.doctype == "Server",
				"doc_method": "cleanup_unused_files",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Enable Autoscale",
				"description": "Setup a secondary application server to autoscale to during high loads",
				"button_label": "Enable",
				"condition": self.status == "Active"
				and self.doctype == "Server"
				and not self.secondary_server
				and not getattr(self, "is_unified_server", False)
				and self.cluster in self._get_clusters_with_autoscale_support(),
				"group": "Application Server Actions",
			},
			{
				"action": "Disable Autoscale",
				"description": "Turn off autoscaling and remove the secondary application server.",
				"button_label": "Disable",
				"condition": (
					self.status == "Active"
					and self.doctype == "Server"
					# Only applicable for primary application servers
					and self.secondary_server
					and self.benches_on_shared_volume
				),
				"group": "Application Server Actions",
			},
			{
				"action": "Drop server",
				"description": "Drop both the application and database servers"
				if not getattr(self, "is_unified_server", False)
				else "Drop the unifed server",
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

	def should_show_reboot(self) -> bool:
		if self.doctype == "Server":
			return True

		if self.doctype == "Database Server":
			return bool(not getattr(self, "is_unified_server", False))

		return False

	def get_data_disk_size(self) -> int:
		"""Get servers data disk size"""
		mountpoint = self.guess_data_disk_mountpoint()
		volume = self.find_mountpoint_volume(mountpoint)

		if not volume:  # Volume might not be attached as soon as the server is created
			return 0

		return frappe.db.get_value(
			"Virtual Machine Volume", {"volume_id": volume.volume_id, "parent": volume.parent}, "size"
		)

	def _get_app_and_database_servers(self) -> tuple[Server, DatabaseServer]:
		if self.doctype == "Database Server":
			app_server_name = frappe.db.get_value("Server", {"database_server": self.name}, "name")
			app_server = frappe.get_doc("Server", app_server_name)
			return app_server, self

		db_server = frappe.get_doc("Database Server", self.database_server)
		return self, db_server

	@dashboard_whitelist()
	def drop_server(self):
		app_server, db_server = self._get_app_and_database_servers()
		app_server.archive()

		# Don't need to archive db server explicitly if it's a unified server
		if app_server.is_unified_server:
			return

		db_server.archive()

	@dashboard_whitelist()
	def toggle_auto_increase_storage(self, enable: bool):
		"""Toggle auto disk increase."""
		app_server, database_server = self._get_app_and_database_servers()

		app_server.auto_increase_storage = enable
		database_server.auto_increase_storage = enable

		app_server.save()
		database_server.save()

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

	@frappe.whitelist()
	def create_dns_record(self):
		try:
			domain = frappe.get_doc("Root Domain", self.domain)

			if domain.generic_dns_provider:
				return

			client = boto3.client(
				"route53",
				aws_access_key_id=domain.aws_access_key_id,
				aws_secret_access_key=domain.get_password("aws_secret_access_key"),
				region_name=domain.aws_region,
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

	def add_to_public_groups(self):
		groups = frappe.get_all("Release Group", {"public": True, "enabled": True}, "name")
		for group_name in groups:
			group: ReleaseGroup = frappe.get_doc("Release Group", group_name)
			with suppress(frappe.ValidationError):
				group.add_server(str(self.name), deploy=True)

	@frappe.whitelist()
	def enable_for_new_benches_and_sites(self):
		if not self.public:
			frappe.throw("Action only allowed for public servers")

		server = self.get_server_enabled_for_new_benches_and_sites()
		self.add_to_public_groups()
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
	def disable_for_new_benches_and_sites(self):
		self.use_for_new_benches = False
		self.use_for_new_sites = False
		self.save()

	def remove_from_public_groups(self, force=False):
		groups: list[str] = frappe.get_all(
			"Release Group",
			{
				"public": True,
				"enabled": True,
			},
			pluck="name",
		)
		active_benches_groups: list[str] = frappe.get_all(
			"Bench", {"status": "Active", "group": ("in", groups), "server": self.name}, pluck="group"
		)
		parent_filter = {"parent": ("in", groups)}
		if not force:
			parent_filter = {"parent": ("in", set(groups) - set(active_benches_groups))}

		frappe.db.delete(
			"Release Group Server",
			{"server": self.name, **parent_filter},
			pluck="parent",
		)

	def validate_cluster(self):
		if not self.cluster:
			self.cluster = frappe.db.get_value("Root Domain", self.domain, "default_cluster")
		if not self.cluster:
			frappe.throw("Default Cluster not found", frappe.ValidationError)

	def validate_agent_password(self):
		# In case of unified servers the agent password is set during creation of the virtual machine
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
	def ping_mariadb(self) -> bool:
		try:
			agent = Agent(self.name, self.doctype)
			return agent.ping_database(self).get("reachable")
		except Exception:
			return False

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
			ansible = None

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
			elif self.provider == "Vodacom":
				ansible = Ansible(playbook="vodacom.yml", server=self, user="ubuntu")

			if self.provider != "Generic" and ansible:
				ansible.run()

			self.reload()
			self.is_server_prepared = True
			self.save()
		except Exception:
			log_error("Server Preparation Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_unified_server(self):
		"""Setup both the application server and its associated database server (unified plays on vm)."""
		frappe.enqueue_doc(self.doctype, self.name, "_setup_unified_server", queue="long", timeout=2400)

	def _setup_unified_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		agent_branch = self.get_agent_repository_branch()
		certificate = self.get_certificate()
		log_server, kibana_password = self.get_log_server()
		agent_sentry_dsn = frappe.db.get_single_value("Press Settings", "agent_sentry_dsn")
		database_server: DatabaseServer = frappe.get_doc("Database Server", self.database_server)
		database_server_config = database_server._get_config()

		self.status = "Installing"
		database_server.status = "Installing"
		self.save()
		database_server.save()

		try:
			ansible = Ansible(
				playbook="unified_server.yml",
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
					"agent_branch": agent_branch,
					"agent_sentry_dsn": agent_sentry_dsn,
					"monitoring_password": self.get_monitoring_password(),
					"log_server": log_server,
					"kibana_password": kibana_password,
					"certificate_private_key": certificate.private_key,
					"certificate_full_chain": certificate.full_chain,
					"certificate_intermediate_chain": certificate.intermediate_chain,
					"docker_depends_on_mounts": self.docker_depends_on_mounts,
					"db_port": database_server.db_port,
					"agent_repository_branch_or_commit_ref": self.get_agent_repository_branch(),
					"agent_update_args": " --skip-repo-setup=true",
					"server_id": database_server.server_id,
					"allocator": database_server.memory_allocator.lower(),
					"mariadb_root_password": database_server_config.mariadb_root_password,
					"mariadb_depends_on_mounts": database_server_config.mariadb_depends_on_mounts,
					**self.get_mount_variables(),  # Currently same as database server since no volumes
				},
			)
			play = ansible.run()
			self.reload()
			database_server = database_server.reload()

			if play.status == "Success":
				self.status = "Active"
				database_server.status = "Active"
			else:
				self.status = "Broken"
				database_server.status = "Broken"
		except Exception:
			self.status = "Broken"
			database_server.status = "Broken"
			log_error("Unified Server Setup Exception", server=self.as_dict())

		self.save()
		database_server.save()

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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
			agent_branch = frappe.get_value("Press Settings", "Press Settings", "branch")
			if not agent_branch:
				agent_branch = "upstream/master"
			else:
				agent_branch = f"upstream/{agent_branch}"
			ansible = Ansible(
				playbook="update_agent.yml",
				variables={
					"agent_repository_url": self.get_agent_repository_url(),
					"agent_repository_branch_or_commit_ref": agent_branch,
					"agent_update_args": " --skip-repo-setup=true",
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

	@dashboard_whitelist()
	@frappe.whitelist()
	def cleanup_unused_files(self, force: bool = False):
		if self.is_build_server():
			return

		with suppress(frappe.DoesNotExistError):
			cleanup_job: "AgentJob" = frappe.get_last_doc(
				"Agent Job", {"server": self.name, "job_type": "Cleanup Unused Files"}
			)
			if cleanup_job.status in ["Running", "Pending"]:
				frappe.throw("Cleanup job is already running")

		self._cleanup_unused_files(force=force)

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

	def _cleanup_unused_files(self, force: bool = False):
		agent = Agent(self.name, self.doctype)
		if agent.should_skip_requests():
			return
		agent.cleanup_unused_files(force)

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
			frappe.log_error(
				title="Error removing glassfile",
				message=e.output.decode(),
				reference_doctype=self.doctype,
				reference_name=self.name,
			)

	def get_server_from_device(self, device: str) -> "BaseServer":
		if self.provider == "Hetzner":
			volume_id = device.removeprefix("/dev/disk/by-id/scsi-0HC_Volume_")
		else:
			volume_id = device.removeprefix("/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_")
			if not volume_id.startswith("vol-"):
				volume_id = volume_id.replace("vol", "vol-", 1)

		virtual_machine = frappe.get_value("Virtual Machine Volume", {"volume_id": volume_id}, "parent")

		if virtual_machine == self.virtual_machine:
			return self

		nfs_server_name = frappe.get_value("NFS Server", {"virtual_machine": virtual_machine}, "name")
		return frappe.get_doc("NFS Server", nfs_server_name)

	@frappe.whitelist()
	def extend_ec2_volume(self, device=None, log: str | None = None):
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
			assert volume is not None, "Volume not found"
			assert volume.volume_id is not None, "Volume ID not found"
			device = self.get_device_from_volume_id(volume.volume_id)

		server = self.get_server_from_device(device)

		try:
			ansible = Ansible(
				playbook="extend_ec2_volume.yml",
				server=server,
				user=server._ssh_user(),
				port=server._ssh_port(),
				variables={"restart_mariadb": restart_mariadb, "device": device},
			)
			play = ansible.run()
			if log:
				frappe.db.set_value("Add On Storage Log", log, "extend_ec2_play", play.name)
				frappe.db.commit()
		except Exception:
			log_error("EC2 Volume Extend Exception", server=server.as_dict())

	def enqueue_extend_ec2_volume(self, device, log):
		frappe.enqueue_doc(
			self.doctype, self.name, "extend_ec2_volume", device=device, log=log, at_front=True, queue="long"
		)

	@cached_property
	def time_to_wait_before_updating_volume(self) -> timedelta | int:
		if self.provider != "AWS EC2":
			return 0

		last_updated_at = frappe.get_value(
			"Virtual Machine Volume",
			{"parent": self.virtual_machine, "idx": 1},  # first volume is likely main
			"last_updated_at",
		)

		if not last_updated_at:
			return 0

		diff = frappe.utils.now_datetime() - last_updated_at
		return diff if diff < timedelta(hours=6) else 0

	@frappe.whitelist()
	def increase_disk_size(self, increment=50, mountpoint=None, log: str | None = None):
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
		assert volume is not None, f"Volume not found for mountpoint {mountpoint}"
		# Get the parent of the volume directly instead of guessing.
		assert volume.parent is not None, "Virtual Machine not found for volume"
		assert volume.volume_id is not None, "Volume ID not found"
		virtual_machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", volume.parent)
		virtual_machine.increase_disk_size(volume.volume_id, increment)
		if self.provider == "AWS EC2":
			device = self.get_device_from_volume_id(volume.volume_id)
			self.enqueue_extend_ec2_volume(device, log)
		elif self.provider == "OCI":
			# TODO: Add support for volumes on OCI
			# Non-boot volumes might not need resize
			self.break_glass()
			self.reboot()

	def guess_data_disk_mountpoint(self) -> str:
		if not hasattr(self, "has_data_volume") or not self.has_data_volume:
			return "/"

		volumes = self.get_volume_mounts()
		if volumes or self.has_data_volume:
			# Adding this condition since this method is called from both server and database server doctypes
			if self.doctype == "Server":
				mountpoint = BENCH_DATA_MNT_POINT
			elif self.doctype == "Database Server":
				mountpoint = MARIADB_DATA_MNT_POINT
		else:
			mountpoint = "/"
		return mountpoint

	def find_mountpoint_volume(self, mountpoint) -> "VirtualMachineVolume" | None:
		volume_id = None
		if self.provider == "Generic":
			return None

		machine: "VirtualMachine" = frappe.get_doc("Virtual Machine", self.virtual_machine)

		if volume_id:
			# Return the volume doc immediately
			return find(machine.volumes, lambda x: x.volume_id == volume_id)

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
				"plan_type": "Server Plan",
				"plan": self.plan,
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
				"plan_type": "Server Storage Plan",
			},
		)
		return frappe.get_doc("Subscription", name) if name else None

	@frappe.whitelist()
	def rename_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_rename_server", queue="long", timeout=2400)

	@frappe.whitelist()
	def archive(self):  # noqa: C901
		if frappe.db.exists(
			"Press Job",
			{
				"job_type": "Archive Server",
				"server": self.name,
				"server_type": self.doctype,
				"status": "Success",
			},
		):
			if self.status != "Archived":
				self.status = "Archived"
				self.save()

			frappe.msgprint(_("Server {0} has already been archived.").format(self.name))
			return

		if self.virtual_machine:
			vm_status = frappe.db.get_value("Virtual Machine", self.virtual_machine, "status")
			if vm_status == "Terminated":
				self.status = "Archived"
				self.save()
				return

		if frappe.get_all(
			"Site",
			filters={"server": self.name, "status": ("!=", "Archived")},
			ignore_ifnull=True,
		):
			frappe.throw(
				_("Cannot archive server with sites. Please drop them from their respective dashboards.")
			)
		if frappe.get_all(
			"Bench",
			filters={"server": self.name, "status": ("!=", "Archived")},
			ignore_ifnull=True,
		):
			frappe.throw(
				_("Cannot archive server with benches. Please drop them from their respective dashboards.")
			)

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

	def can_change_plan(  # noqa: C901
		self, ignore_card_setup: bool, new_plan: ServerPlan, upgrade_disk: bool = False
	) -> None:
		if is_system_user(frappe.session.user):
			return

		if ignore_card_setup:
			return

		team = frappe.get_doc("Team", self.team)

		if team.parent_team:
			team = frappe.get_doc("Team", team.parent_team)

		if team.payment_mode == "Paid By Partner" and team.billing_team:
			team = frappe.get_doc("Team", team.billing_team)

		if not (team.default_payment_method or team.get_balance()):
			frappe.throw("Cannot change plan because you haven't added a card and not have enough balance")

		cluster: Cluster = frappe.get_doc("Cluster", self.cluster)
		if not cluster.check_machine_availability(new_plan.instance_type):
			frappe.throw(
				f"Cannot change plan right now since the instance type {new_plan.instance_type} is not available. Try again later."
			)

		if self.provider == "Hetzner" and self.plan and self.plan == new_plan.name and upgrade_disk:
			current_root_disk_size = frappe.db.get_value(
				"Virtual Machine", self.virtual_machine, "root_disk_size"
			)
			if current_root_disk_size >= new_plan.disk:
				frappe.throw(
					"Cannot upgrade disk because the selected plan has the same or smaller disk size"
				)

	@dashboard_whitelist()
	def change_plan(self, plan: str, ignore_card_setup=False, upgrade_disk: bool = False):
		plan_doc: ServerPlan = frappe.get_doc("Server Plan", plan)
		self.can_change_plan(ignore_card_setup, new_plan=plan_doc, upgrade_disk=upgrade_disk)
		self._change_plan(plan_doc)
		self.run_press_job(
			"Resize Server", {"machine_type": plan_doc.instance_type, "upgrade_disk": upgrade_disk}
		)

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

	def run_press_job(self, job_name, arguments=None) -> PressJob:
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
	def setup_nfs(self):
		"""Allow nfs setup on this server"""
		frappe.enqueue_doc(self.doctype, self.name, "_setup_nfs", queue="long", timeout=1200)

	def _setup_nfs(self):
		try:
			ansible = Ansible(
				playbook="nfs_server.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Exception while setting up NFS", doc=self)

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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
			ansible = Ansible(
				playbook="glass_file.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
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
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("MySQLdump Setup Exception", doc=self)

	def setup_iptables(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_iptables")

	def _setup_iptables(self):
		try:
			ansible = Ansible(
				playbook="iptables.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Iptables Setup Exception", doc=self)

	@frappe.whitelist()
	def set_swappiness(self):
		frappe.enqueue_doc(self.doctype, self.name, "_set_swappiness")

	def _set_swappiness(self):
		try:
			ansible = Ansible(
				playbook="swappiness.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Swappiness Setup Exception", doc=self)

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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
		if self.provider not in ("AWS EC2", "OCI", "DigitalOcean", "Hetzner"):
			raise NotImplementedError
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
			if volume.device == "/dev/sda1" or (self.provider == "Hetzner" and volume.device == "/dev/sda"):
				# Skip root volume. This is for AWS other providers may have different root volume
				continue
			self.append("mounts", {"volume_id": volume.volume_id})

	def set_default_mount_points(self):
		first = self.mounts[0]
		if self.doctype == "Server":
			first.mount_point = BENCH_DATA_MNT_POINT
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/home/frappe/benches",
					"source": f"{BENCH_DATA_MNT_POINT}/home/frappe/benches",
					"mount_point_owner": "frappe",
					"mount_point_group": "frappe",
				},
			)
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/var/lib/docker",
					"source": f"{BENCH_DATA_MNT_POINT}/var/lib/docker",
					"mount_point_owner": "root",
					"mount_point_group": "root",
				},
			)
		elif self.doctype == "Database Server":
			first.mount_point = MARIADB_DATA_MNT_POINT
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/var/lib/mysql",
					"source": f"{MARIADB_DATA_MNT_POINT}/var/lib/mysql",
					"mount_point_owner": "mysql",
					"mount_point_group": "mysql",
				},
			)
			self.append(
				"mounts",
				{
					"mount_type": "Bind",
					"mount_point": "/etc/mysql",
					"source": f"{MARIADB_DATA_MNT_POINT}/etc/mysql",
					"mount_point_owner": "mysql",
					"mount_point_group": "mysql",
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
		if self.provider == "Hetzner":
			return f"/dev/disk/by-id/scsi-0HC_Volume_{volume_id}"
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

	def _create_arm_build(self, build: str) -> str | None:
		from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
			_create_arm_build as arm_build_util,
		)

		deploy_candidate = frappe.get_value("Deploy Candidate Build", build, "deploy_candidate")

		try:
			return arm_build_util(deploy_candidate)
		except frappe.ValidationError:
			frappe.log_error(
				"Failed to create ARM build", message=f"Failed to create arm build for build {build}"
			)
			return None

	def _process_bench(self, bench_info: BenchInfoType) -> ARMDockerImageType:
		candidate = bench_info["candidate"]
		build_id = bench_info["build"]

		arm_build = frappe.get_value("Deploy Candidate", candidate, "arm_build")

		if arm_build:
			return {
				"build": arm_build,
				"status": frappe.get_value("Deploy Candidate Build", arm_build, "status"),
				"bench": bench_info["name"],
			}

		new_arm_build = self._create_arm_build(build_id)
		return {
			"build": new_arm_build,
			"status": "Pending",
			"bench": bench_info["name"],
		}

	def _get_dependency_version(self, candidate: str, dependency: str) -> str:
		return frappe.get_value(
			"Deploy Candidate Dependency",
			{"parent": candidate, "dependency": dependency},
			"version",
		)

	@frappe.whitelist()
	def collect_arm_images(self) -> str:
		"""Collect arm build images of all active benches on VM"""
		# Need to disable all further deployments before collecting arm images.

		def _parse_semantic_version(version_str: str) -> semantic_version.Version:
			try:
				return semantic_version.Version(version_str)
			except ValueError:
				return semantic_version.Version(f"{version_str}.0")

		frappe.db.set_value("Server", self.name, "stop_deployments", 1)
		frappe.db.commit()

		benches = frappe.get_all(
			"Bench",
			{"server": self.name, "status": "Active"},
			["name", "build", "candidate"],
		)

		if not benches:
			frappe.throw(f"No active benches found on <a href='/app/server/{self.name}'>Server</a>")

		for bench in benches:
			raw_bench_version = self._get_dependency_version(bench["candidate"], "BENCH_VERSION")
			raw_python_version = self._get_dependency_version(bench["candidate"], "PYTHON_VERSION")
			bench_version = _parse_semantic_version(raw_bench_version)
			python_version = _parse_semantic_version(raw_python_version)

			if python_version > semantic_version.Version(
				"3.8.0"
			) and bench_version < semantic_version.Version("5.25.1"):
				frappe.db.set_value(
					"Deploy Candidate Dependency",
					{"parent": bench["candidate"], "dependency": "BENCH_VERSION"},
					"version",
					"5.25.1",
				)

		frappe.db.commit()

		arm_build_record: ARMBuildRecord = frappe.new_doc("ARM Build Record", server=self.name)

		for bench_info in benches:
			arm_build_record.append("arm_images", self._process_bench(bench_info))

		arm_build_record.save()
		return f"<a href=/app/arm-build-record/{arm_build_record.name}> ARM Build Record"

	@frappe.whitelist()
	def start_active_benches(self):
		benches = frappe.get_all("Bench", {"server": self.name, "status": "Active"}, pluck="name")
		frappe.enqueue_doc(self.doctype, self.name, "_start_active_benches", benches=benches)

	def _start_active_benches(self, benches: list[str]):
		try:
			ansible = Ansible(
				playbook="start_benches.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={"benches": " ".join(benches)},
			)
			ansible.run()
		except Exception:
			log_error("Start Benches Exception", server=self.as_dict())

	def _stop_active_benches(self):
		try:
			ansible = Ansible(
				playbook="stop_benches.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Start Benches Exception", server=self.as_dict())

	@frappe.whitelist()
	def mount_volumes(
		self,
		now: bool | None,
		stop_docker_before_mount: bool | None = None,
		stop_mariadb_before_mount: bool | None = None,
		start_docker_after_mount: bool | None = None,
		start_mariadb_after_mount: bool | None = None,
		cleanup_db_replication_files: bool | None = None,
		rotate_additional_volume_metadata: bool | None = None,
	):
		if not cleanup_db_replication_files:
			cleanup_db_replication_files = False

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_mount_volumes",
			queue="long",
			timeout=7200,
			at_front=True,
			now=now or False,
			stop_docker_before_mount=stop_docker_before_mount or False,
			stop_mariadb_before_mount=stop_mariadb_before_mount or False,
			start_docker_after_mount=start_docker_after_mount or False,
			start_mariadb_after_mount=start_mariadb_after_mount or False,
			cleanup_db_replication_files=cleanup_db_replication_files,
			rotate_additional_volume_metadata=rotate_additional_volume_metadata or False,
		)

	def _mount_volumes(
		self,
		stop_docker_before_mount: bool = False,
		stop_mariadb_before_mount: bool = False,
		start_docker_after_mount: bool = False,
		start_mariadb_after_mount: bool = False,
		cleanup_db_replication_files: bool = False,
		rotate_additional_volume_metadata: bool = False,
	):
		try:
			variables = {
				"stop_docker_before_mount": self.doctype == "Server" and stop_docker_before_mount,
				"stop_mariadb_before_mount": self.doctype == "Database Server" and stop_mariadb_before_mount,
				"start_docker_after_mount": self.doctype == "Server" and start_docker_after_mount,
				"start_mariadb_after_mount": self.doctype == "Database Server" and start_mariadb_after_mount,
				# If other services are stopped, we can skip filebeat restart
				"stop_filebeat_before_mount": stop_docker_before_mount or stop_mariadb_before_mount,
				"start_filebeat_after_mount": stop_docker_before_mount or stop_mariadb_before_mount,
				"cleanup_db_replication_files": cleanup_db_replication_files,
				"rotate_additional_volume_metadata": rotate_additional_volume_metadata,
				"hetzner_cloud": self.provider == "Hetzner",
				**self.get_mount_variables(),
			}
			if self.provider != "Generic" and (
				self.doctype == "Database Server" or getattr(self, "has_unified_volume", False)
			):
				variables["mariadb_bind_address"] = frappe.get_value(
					"Virtual Machine", self.virtual_machine, "private_ip_address"
				)

			ansible = Ansible(
				playbook="mount.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables=variables,
			)
			play = ansible.run()
			self.reload()
			if self._set_mount_status(play):
				self.save()
		except Exception:
			log_error("Server Mount Exception", server=self.as_dict())

	def _set_mount_status(self, play):  # noqa: C901
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
						self.mounts,
						lambda x: x.name == row.get("item", {}).get("original_item", {}).get("name"),
					)
				if not mount:
					mount = find(
						self.mounts, lambda x: x.name == row.get("item", {}).get("item", {}).get("name")
					)
				if not mount:
					mount = find(
						self.mounts,
						lambda x: x.name
						== row.get("item", {}).get("item", {}).get("original_item", {}).get("name"),
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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
		projected_usage = self.disk_capacity(mountpoint) - self.space_available_in_6_hours(mountpoint) * 5
		projected_growth_gb = abs(projected_usage) / (4 * 1024 * 1024 * 1024)

		if mountpoint == "/" and self.guess_data_disk_mountpoint() != "/":
			# Ingore limits set in case of mountpoint being /
			return int(projected_growth_gb)

		return int(max(self.auto_add_storage_min, min(projected_growth_gb, self.auto_add_storage_max)))

	def recommend_disk_increase(self, mountpoint: str):
		"""
		Send disk expansion email to users with disabled auto addon storage at 80% capacity
		Calculate the disk usage over a 30 hour period and take 25 percent of that
		"""
		server: Server | DatabaseServer = frappe.get_doc(self.doctype, self.name)  # type: ignore
		if server.auto_increase_storage:
			return

		disk_capacity = self.disk_capacity(mountpoint)
		current_disk_usage = disk_capacity - self.free_space(mountpoint)
		recommended_increase = (
			abs(self.disk_capacity(mountpoint) - self.space_available_in_6_hours(mountpoint) * 5)
			/ 4
			/ 1024
			/ 1024
			/ 1024
		)

		current_disk_usage_flt = round(current_disk_usage / 1024 / 1024 / 1024, 2)
		disk_capacity_flt = round(disk_capacity / 1024 / 1024 / 1024, 2)

		frappe.sendmail(
			recipients=get_communication_info("Email", "Incident", self.doctype, self.name),
			subject=f"Important: Server {server.name} has used 80% of the available space",
			template="disabled_auto_disk_expansion",
			args={
				"server": server.name,
				"current_disk_usage": f"{current_disk_usage_flt} Gib",
				"available_disk_space": f"{disk_capacity_flt} GiB",
				"used_storage_percentage": "80%",
				"increase_by": f"{recommended_increase} GiB",
			},
		)

	def calculated_increase_disk_size(
		self,
		mountpoint: str,
		additional: int = 0,
	):
		"""
		Calculate required disk increase for servers and handle notifications accordingly.
			- For servers with `auto_increase_storage` enabled:
				- Compute the required storage increase.
				- Automatically apply the increase.
				- Send an email notification about the auto-added storage.
			- For servers with `auto_increase_storage` disabled:
				- If disk usage exceeds 90%, send a warning email.
				- We have also sent them emails at 80% if they haven't enabled auto add on yet then send here again.
				- Notify the user to manually increase disk space.
		"""

		buffer = self.size_to_increase_by_for_20_percent_available(mountpoint)
		server: Server | DatabaseServer = frappe.get_doc(self.doctype, self.name)
		disk_capacity = self.disk_capacity(mountpoint)

		current_disk_usage = round((disk_capacity - self.free_space(mountpoint)) / 1024 / 1024 / 1024, 2)

		if not server.auto_increase_storage and (not server.has_data_volume or mountpoint != "/"):
			TelegramMessage.enqueue(
				f"Not increasing disk (mount point {mountpoint}) on "
				f"[{self.name}]({frappe.utils.get_url_to_form(self.doctype, self.name)}) "
				f"by {buffer + additional}G as auto disk increase disabled by user",
				"Information",
			)
			insert_addon_storage_log(
				adding_storage=additional + buffer,
				available_disk_space=round((self.disk_capacity(mountpoint) / 1024 / 1024 / 1024), 2),
				current_disk_usage=current_disk_usage
				or round(
					(self.disk_capacity(mountpoint) - self.free_space(mountpoint)) / 1024 / 1024 / 1024, 2
				),
				mountpoint=mountpoint or self.guess_data_disk_mountpoint(),
				is_auto_triggered=True,
				is_warning=True,
				database_server=server.name if server.name[0] == "m" else None,
				server=server.name if server.name[0] == "f" else None,
			)

			return

		TelegramMessage.enqueue(
			f"Increasing disk (mount point {mountpoint}) on "
			f"[{self.name}]({frappe.utils.get_url_to_form(self.doctype, self.name)}) "
			f"by {buffer + additional}G",
			"Information",
		)

		self.increase_disk_size_for_server(
			self.name,
			buffer + additional,
			mountpoint,
			is_auto_triggered=True,
			current_disk_usage=current_disk_usage,
		)

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
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Prune Docker System Exception", doc=self)

	@frappe.whitelist()
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
			user=primary._ssh_user(),
			port=primary._ssh_port(),
		)
		play = ansible.run()
		if play.status == "Success":
			return frappe.db.get_value(self.doctype, self.primary, "frappe_public_key")
		frappe.throw(f"Failed to fetch {primary.name}'s Frappe public key")
		return None

	def copy_files(self, source, destination, extra_options=None):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_copy_files",
			source=source,
			destination=destination,
			extra_options=extra_options,
			queue="long",
			timeout=7200,
		)

	def _copy_files(self, source, destination, extra_options=None):
		try:
			ansible = Ansible(
				playbook="copy.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"source": source,
					"destination": destination,
					"extra_options": extra_options,
				},
			)
			ansible.run()
		except Exception:
			log_error("Sever File Copy Exception", server=self.as_dict())

	@frappe.whitelist()
	def setup_logrotate(self):
		"""Setup monitor json & mariadb logrotate"""
		frappe.enqueue_doc(self.doctype, self.name, "_setup_logrotate", queue="long", timeout=1200)

	@frappe.whitelist()
	def install_cadvisor(self):
		frappe.enqueue_doc(self.doctype, self.name, "_install_cadvisor")

	def _install_cadvisor(self):
		try:
			ansible = Ansible(
				playbook="install_cadvisor.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Cadvisor Install Exception", server=self.as_dict())

	def set_additional_unified_config(self):
		"""Set both `Server` and `Database Server` additional config for Unified Servers"""
		# Common config for both Server and Database Server
		self.set_swappiness()
		self.add_glass_file()
		self.install_filebeat()

		# Server specific config
		self.setup_mysqldump()
		self.install_earlyoom()
		self.setup_ncdu()
		self.setup_iptables()
		self.install_cadvisor()
		self.setup_logrotate()  # Logrotate monitor json

		# Database Server specific config
		database_server: DatabaseServer = frappe.get_doc("Database Server", self.database_server)
		default_variables = frappe.get_all("MariaDB Variable", {"set_on_new_servers": 1}, pluck="name")
		for var_name in default_variables:
			var: MariaDBVariable = frappe.get_doc("MariaDB Variable", var_name)
			var.set_on_server(database_server)

		database_server.adjust_memory_config()
		database_server.provide_frappe_user_du_and_find_permission()
		database_server.setup_logrotate()  # Logrotate mariadb logs
		database_server.setup_user_lingering()

		self.validate_mounts()
		self.save(ignore_permissions=True)

	@frappe.whitelist()
	def set_additional_config(self):  # noqa: C901
		"""
		Corresponds to Set additional config step in Create Server Press Job
		"""

		if hasattr(self, "is_unified_server") and self.is_unified_server:
			self.set_additional_unified_config()
			return

		if self.doctype == "Database Server":
			default_variables = frappe.get_all("MariaDB Variable", {"set_on_new_servers": 1}, pluck="name")
			for var_name in default_variables:
				var: MariaDBVariable = frappe.get_doc("MariaDB Variable", var_name)
				var.set_on_server(self)
			if self.has_data_volume:
				self.add_or_update_mariadb_variable("tmpdir", "value_str", "/opt/volumes/mariadb/tmp")

		self.set_swappiness()
		self.add_glass_file()
		self.install_filebeat()
		self.setup_logrotate()

		if self.doctype == "Server":
			self.install_nfs_common()
			self.setup_mysqldump()
			self.install_earlyoom()
			self.setup_ncdu()
			self.setup_iptables()

			if self.has_data_volume:
				self.setup_archived_folder()

			self.install_cadvisor()

			if self.is_secondary:
				frappe.db.set_value(
					"Server", {"secondary_server": self.name}, "status", self.status
				)  # Update the status of the primary server
				frappe.db.commit()

		if self.doctype == "Database Server":
			self.adjust_memory_config()
			self.provide_frappe_user_du_and_find_permission()
			self.setup_user_lingering()

			if self.has_data_volume:
				self.setup_binlog_indexes_folder()

		if self.doctype == "Proxy Server":
			self.setup_wildcard_hosts()

		self.validate_mounts()
		self.save(ignore_permissions=True)

	def get_wildcard_domains(self):
		wildcard_domains = []
		for domain in self.domains:
			if domain.domain == self.domain and self.doctype == "Proxy Server":
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
					"code_server": domain.code_server,
				}
			)
		return wildcard_domains

	@frappe.whitelist()
	def setup_wildcard_hosts(self):
		agent = Agent(self.name, server_type=self.doctype)
		wildcards = self.get_wildcard_domains()
		return agent.setup_wildcard_hosts(wildcards)

	@property
	def bastion_host(self):
		if self.bastion_server:
			return frappe.get_cached_value(
				"Bastion Server", self.bastion_server, ["ssh_user", "ssh_port", "ip"], as_dict=True
			)
		return frappe._dict()

	@frappe.whitelist()
	def get_aws_static_ip(self):
		if self.provider != "AWS EC2":
			frappe.throw("Failed to proceed as VM is not AWS EC2")

		vm_doc = frappe.get_doc("Virtual Machine", self.virtual_machine)

		cluster_doc = frappe.get_doc("Cluster", self.cluster)
		region_name = cluster_doc.region
		aws_access_key_id = cluster_doc.aws_access_key_id
		aws_secret_access_key = get_decrypted_password(
			"Cluster", self.cluster, fieldname="aws_secret_access_key"
		)

		instance_id = vm_doc.instance_id

		# Initialize EC2 client
		ec2_client = boto3.client(
			"ec2",
			aws_access_key_id=aws_access_key_id,
			aws_secret_access_key=aws_secret_access_key,
			region_name=region_name,
		)

		# Allocate new Elastic IP
		allocation = ec2_client.allocate_address(Domain="vpc")
		allocation_id = allocation["AllocationId"]
		public_ip = allocation["PublicIp"]

		# Associate with instance
		ec2_client.associate_address(InstanceId=instance_id, AllocationId=allocation_id)

		# Trigger VM sync
		vm_doc.sync()

		return f"Static IP {public_ip} alloted to the VM (Allocation ID: {allocation_id})"


class Server(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.auto_scale_trigger.auto_scale_trigger import AutoScaleTrigger
		from press.press.doctype.communication_info.communication_info import CommunicationInfo
		from press.press.doctype.resource_tag.resource_tag import ResourceTag
		from press.press.doctype.server_mount.server_mount import ServerMount

		agent_password: DF.Password | None
		auto_add_storage_max: DF.Int
		auto_add_storage_min: DF.Int
		auto_increase_storage: DF.Check
		auto_scale_trigger: DF.Table[AutoScaleTrigger]
		bastion_server: DF.Link | None
		benches_on_shared_volume: DF.Check
		cluster: DF.Link | None
		communication_infos: DF.Table[CommunicationInfo]
		database_server: DF.Link | None
		disable_agent_job_auto_retry: DF.Check
		domain: DF.Link | None
		enable_logical_replication_during_site_update: DF.Check
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		halt_agent_jobs: DF.Check
		has_data_volume: DF.Check
		hostname: DF.Data
		hostname_abbreviation: DF.Data | None
		ignore_incidents_till: DF.Datetime | None
		ip: DF.Data | None
		ipv6: DF.Data | None
		is_for_recovery: DF.Check
		is_managed_database: DF.Check
		is_monitoring_disabled: DF.Check
		is_primary: DF.Check
		is_provisioning_press_job_completed: DF.Check
		is_pyspy_setup: DF.Check
		is_replication_setup: DF.Check
		is_secondary: DF.Check
		is_self_hosted: DF.Check
		is_server_prepared: DF.Check
		is_server_renamed: DF.Check
		is_server_setup: DF.Check
		is_standalone: DF.Check
		is_standalone_setup: DF.Check
		is_static_ip: DF.Check
		is_unified_server: DF.Check
		is_upstream_setup: DF.Check
		keep_files_on_server_in_offsite_backup: DF.Check
		managed_database_service: DF.Link | None
		mounts: DF.Table[ServerMount]
		new_worker_allocation: DF.Check
		plan: DF.Link | None
		platform: DF.Literal["x86_64", "arm64"]
		primary: DF.Link | None
		private_ip: DF.Data | None
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI", "Hetzner", "Vodacom", "DigitalOcean"]
		proxy_server: DF.Link | None
		public: DF.Check
		ram: DF.Float
		root_public_key: DF.Code | None
		scaled_up: DF.Check
		secondary_server: DF.Link | None
		self_hosted_mariadb_root_password: DF.Password | None
		self_hosted_mariadb_server: DF.Data | None
		self_hosted_server_domain: DF.Data | None
		set_bench_memory_limits: DF.Check
		skip_scheduled_backups: DF.Check
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		staging: DF.Check
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		stop_deployments: DF.Check
		tags: DF.Table[ResourceTag]
		team: DF.Link | None
		title: DF.Data | None
		tls_certificate_renewal_failed: DF.Check
		use_agent_job_callbacks: DF.Check
		use_for_build: DF.Check
		use_for_new_benches: DF.Check
		use_for_new_sites: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	GUNICORN_MEMORY = 150  # avg ram usage of 1 gunicorn worker
	BACKGROUND_JOB_MEMORY = 3 * 80  # avg ram usage of 3 sets of bg workers

	@role_guard.action()
	def validate(self):
		super().validate()
		self.validate_managed_database_service()

	def validate_managed_database_service(self):
		if getattr(self, "is_managed_database", 0):
			if not self.managed_database_service:
				frappe.throw(_("Please select Managed Database Service"))
			self.database_server = ""
		else:
			self.managed_database_service = ""

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
			self.update_db_server()

		self.set_bench_memory_limits_if_needed(save=False)
		if self.public:
			self.auto_add_storage_min = max(self.auto_add_storage_min, PUBLIC_SERVER_AUTO_ADD_STORAGE_MIN)

		if (
			not self.is_new()
			and self.has_value_changed("enable_logical_replication_during_site_update")
			and self.enable_logical_replication_during_site_update
			and frappe.db.count("Site", {"server": self.name, "status": ("!=", "Archived")}) > 1
		):
			# Throw error if multiple sites are present on the server
			frappe.throw(
				"Cannot enable logical replication during site update if multiple sites are present on the server"
			)

	def update_db_server(self):
		if not self.database_server:
			return
		db_server = frappe.get_doc("Database Server", self.database_server)
		if self.team == db_server.team:
			return

		db_server.team = self.team
		db_server.save()

	def set_bench_memory_limits_if_needed(self, save: bool = False):
		# Enable bench memory limits for public servers
		if self.public:
			self.set_bench_memory_limits = True
		else:
			self.set_bench_memory_limits = False

		if save:
			self.save()

	def get_actions(self):
		server_actions = super().get_actions()

		return [
			{
				"action": "Notification Settings",
				"description": "Manage notification channels",
				"button_label": "Manage",
				"doc_method": "dummy",
				"group": "Application Server Actions" if not self.is_unified_server else "Server Actions",
				"server_doctype": "Server",
				"server_name": self.name,
			},
			*server_actions,
		]

	def update_subscription(self):
		subscription = self.subscription
		if subscription:
			if sub := frappe.db.get_value(
				"Subscription",
				{
					"document_type": self.doctype,
					"document_name": self.name,
					"team": self.team,
					"plan_type": "Server Plan",
					"plan": self.plan,
				},
			):
				frappe.db.set_value("Subscription", sub, "enabled", 1)
				subscription.disable()
			else:
				frappe.db.set_value("Subscription", subscription.name, {"team": self.team, "enabled": 1})
		else:
			try:
				# create new subscription
				self.create_subscription(self.plan)
			except Exception:
				frappe.log_error("Server Subscription Creation Error")

		add_on_storage_subscription = self.add_on_storage_subscription
		if add_on_storage_subscription:
			if existing_subscription := frappe.db.get_value(
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
					existing_subscription,
					{
						"enabled": 1,
						"additional_storage": add_on_storage_subscription.additional_storage,
					},
				)
				add_on_storage_subscription.disable()
			else:
				frappe.db.set_value(
					"Subscription", add_on_storage_subscription.name, {"team": self.team, "enabled": 1}
				)

	def create_secondary_server(self, plan_name: str) -> None:
		"""Create a secondary server for this server"""
		plan: ServerPlan = frappe.get_cached_doc("Server Plan", plan_name)
		team_name = frappe.db.get_value("Server", self.name, "team", "name")
		cluster: "Cluster" = frappe.get_cached_doc("Cluster", self.cluster)
		server_title = f"Secondary - {self.title or self.name}"

		# This is horrible code, however it seems to be the standard
		# https://github.com/frappe/press/blob/28c9ba67b15b5d8ba64e302d084d3289ea744c39/press/api/server.py/#L228-L229
		cluster.database_server = self.database_server
		cluster.proxy_server = self.proxy_server

		secondary_server, _ = cluster.create_server(
			"Server",
			server_title,
			plan,
			team=team_name,
			auto_increase_storage=self.auto_increase_storage,
			is_secondary=True,
			primary=self.name,
		)

		self.secondary_server = secondary_server.name
		self.save()

	def drop_secondary_server(self) -> None:
		"""Drop secondary server"""
		server: "Server" = frappe.get_doc("Server", self.secondary_server)
		server.archive()

	def _setup_logrotate(self):
		try:
			ansible = Ansible(
				playbook="rotate_monitor_json_logs.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Logrotate Setup Exception", server=self.as_dict())

	@dashboard_whitelist()
	@frappe.whitelist()
	def setup_secondary_server(self, server_plan: str):
		"""Setup secondary server"""
		if self.doctype == "Database Server" or self.is_secondary:
			return

		self.setup_nfs()  # Setup nfs when creating a secondary server
		self.status = "Installing"
		self.save()

		self.create_secondary_server(server_plan)

	@dashboard_whitelist()
	@frappe.whitelist()
	def teardown_secondary_server(self):
		if self.secondary_server:
			nfs_volume_detachment: "NFSVolumeDetachment" = frappe.get_doc(
				{"doctype": "NFS Volume Detachment", "primary_server": self.name}
			)
			nfs_volume_detachment.insert(ignore_permissions=True)

	@frappe.whitelist()
	def setup_ncdu(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_ncdu")

	@frappe.whitelist()
	def install_nfs_common(self):
		"""Install nfs common on this server"""
		frappe.enqueue_doc(self.doctype, self.name, "_install_nfs_common")

	def _install_nfs_common(self):
		try:
			ansible = Ansible(
				playbook="install_nfs_common.yml", server=self, user=self._ssh_user(), port=self._ssh_port()
			)
			ansible.run()
		except Exception:
			log_error("Unable to install nfs common", server=self.as_dict())

	def _setup_ncdu(self):
		try:
			ansible = Ansible(
				playbook="install_and_setup_ncdu.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Install and ncdu Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def add_upstream_to_proxy(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_server(self.name)

	def ansible_run(self, command: str) -> dict[str, str]:
		inventory = f"{self.ip},"
		return AnsibleAdHoc(sources=inventory).run(command, self.name)[0]

	def setup_docker(self, now: bool | None = None):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_docker", timeout=1200, now=now or False)

	def _setup_docker(self):
		try:
			ansible = Ansible(
				playbook="docker.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Docker Setup Exception", server=self.as_dict())

	def setup_archived_folder(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup_archived_folder",
			queue="short",
			timeout=1200,
		)

	def _setup_archived_folder(self):
		try:
			ansible = Ansible(
				playbook="setup_archived_folder.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Archived folder setup error", server=self.as_dict())

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		agent_branch = self.get_agent_repository_branch()
		certificate = self.get_certificate()
		log_server, kibana_password = self.get_log_server()
		agent_sentry_dsn = frappe.db.get_single_value("Press Settings", "agent_sentry_dsn")

		# If database server is set, then define db port under configuration
		db_port = (
			frappe.db.get_value("Database Server", self.database_server, "db_port")
			if self.database_server
			else None
		)

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
					"agent_branch": agent_branch,
					"agent_sentry_dsn": agent_sentry_dsn,
					"monitoring_password": self.get_monitoring_password(),
					"log_server": log_server,
					"kibana_password": kibana_password,
					"certificate_private_key": certificate.private_key,
					"certificate_full_chain": certificate.full_chain,
					"certificate_intermediate_chain": certificate.intermediate_chain,
					"docker_depends_on_mounts": self.docker_depends_on_mounts,
					"db_port": db_port,
					"agent_repository_branch_or_commit_ref": self.get_agent_repository_branch(),
					"agent_update_args": " --skip-repo-setup=true",
					**self.get_mount_variables(),
				},
			)
			play = ansible.run()
			self.reload()
			self._set_mount_status(play)
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
				if self.provider == "DigitalOcean":
					# To adjust docker permissions
					self.reboot()
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Server Setup Exception", server=self.as_dict())
		self.save()

	def get_proxy_ip(self):
		# In case of standalone setup, proxy is not required.
		if self.is_standalone:
			return self.ip
		private_ip = frappe.db.get_value("Proxy Server", self.proxy_server, "private_ip")
		with_mask = private_ip + "/24"
		return str(ipaddress.ip_network(with_mask, strict=False))

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
				self.setup_wildcard_hosts()
				self.update_benches_nginx()
		except Exception:
			log_error("Standalone Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def update_benches_nginx(self):
		"""Update benches config for all benches in the server"""
		benches = frappe.get_all("Bench", "name", {"server": self.name, "status": "Active"}, pluck="name")
		for bench_name in benches:
			bench: Bench = frappe.get_doc("Bench", bench_name)
			bench.generate_nginx_config()

	@frappe.whitelist()
	def setup_agent_sentry(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_agent_sentry")

	def _setup_agent_sentry(self):
		agent_sentry_dsn = frappe.db.get_single_value("Press Settings", "agent_sentry_dsn")
		try:
			ansible = Ansible(
				playbook="agent_sentry.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
		secondary_private_ip, secondary_ssh_port = frappe.db.get_value(
			"Server", secondary, ("private_ip", "ssh_port")
		)
		try:
			ansible = Ansible(
				playbook="primary_app.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"secondary_private_ip": secondary_private_ip,
					"secondary_ssh_port": secondary_ssh_port,
				},
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
				user=self._ssh_user(),
				port=self._ssh_port(),
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
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"private_ip": self.private_ip,
					"monitoring_password": monitoring_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Exporters Install Exception", server=self.as_dict())

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
	def max_gunicorn_workers(self) -> float:
		usable_ram_for_gunicorn = 0.6 * self.usable_ram  # 60% of usable ram
		return usable_ram_for_gunicorn / self.GUNICORN_MEMORY

	@cached_property
	def max_bg_workers(self) -> float:
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
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Earlyoom Install Exception", server=self.as_dict())

	@frappe.whitelist()
	def install_wazuh_agent(self):
		wazuh_server = frappe.get_value("Press Settings", "Press Settings", "wazuh_server")
		if not wazuh_server:
			frappe.throw("Please configure Wazuh Server in Press Settings")
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_install_wazuh_agent",
			wazuh_server=wazuh_server,
		)

	def _install_wazuh_agent(self, wazuh_server: str):
		try:
			ansible = Ansible(
				playbook="wazuh_agent_install.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"wazuh_manager": wazuh_server,
					"wazuh_agent_name": self.name,
				},
			)
			ansible.run()
		except Exception:
			log_error("Wazuh Agent Install Exception", server=self.as_dict())

	@frappe.whitelist()
	def uninstall_wazuh_agent(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_uninstall_wazuh_agent",
		)

	def _uninstall_wazuh_agent(self):
		try:
			ansible = Ansible(
				playbook="wazuh_agent_uninstall.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Wazuh Agent Uninstall Exception", server=self.as_dict())

	@property
	def docker_depends_on_mounts(self):
		mount_points = set(mount.mount_point for mount in self.mounts)
		bench_mount_points = set(["/home/frappe/benches"])
		return bench_mount_points.issubset(mount_points)

	@dashboard_whitelist()
	def create_snapshot(self, consistent: bool = False) -> str:
		return self._create_snapshot(consistent)

	def _create_snapshot(
		self, consistent: bool = False, expire_at: datetime.datetime | None = None, free: bool = False
	) -> str:
		doc = frappe.get_doc(
			{
				"doctype": "Server Snapshot",
				"app_server": self.name,
				"consistent": consistent,
				"expire_at": expire_at,
				"free": free,
			}
		).insert(ignore_permissions=True)
		frappe.msgprint(
			f"Snapshot created successfully. <a href='/app/server-snapshot/{doc.name}' target='_blank'>Check Here</a>"
		)
		return doc.name

	@dashboard_whitelist()
	def delete_snapshot(self, snapshot_name: str) -> None:
		doc = frappe.get_doc("Server Snapshot", snapshot_name)
		if doc.app_server != self.name:
			frappe.throw("Snapshot does not belong to this server")
		doc.delete_snapshots()

	@dashboard_whitelist()
	def lock_snapshot(self, snapshot_name: str) -> None:
		doc = frappe.get_doc("Server Snapshot", snapshot_name)
		if doc.app_server != self.name:
			frappe.throw("Snapshot does not belong to this server")
		doc.lock()

	@dashboard_whitelist()
	def unlock_snapshot(self, snapshot_name: str) -> None:
		doc = frappe.get_doc("Server Snapshot", snapshot_name)
		if doc.app_server != self.name:
			frappe.throw("Snapshot does not belong to this server")
		doc.unlock()

	def validate_bench_status_before_scaling(self) -> bool:
		"Ensures no new bench job is pending/running before scaling"
		return bool(
			frappe.db.get_value(
				"Bench", {"server": self.name, "status": ("IN", ["Pending", "Installing", "Updating"])}
			)
		)

	def validate_scale(self):
		"""
		Check if the server can auto scale, the following parameters before creating a scale record
			- Benches being modified
			- Server is configured for auto scale.
			- Was the last auto scale modified before the cool of period (don't create new auto scale).
			- There is a auto scale operation running on the server.
			- There are no active sites on the server.
			- Check if there are active deployments on primary server
		"""
		if not self.can_scale:
			frappe.throw("Server is not configured for auto scaling", frappe.ValidationError)

		if self.validate_bench_status_before_scaling():
			frappe.throw(
				"Please wait for all bench related jobs to complete before scaling the server.",
			)

		last_auto_scale_at = frappe.db.get_value(
			"Auto Scale Record", {"primary_server": self.name, "status": "Success"}, "modified"
		)
		cool_off_period = frappe.db.get_single_value("Press Settings", "cool_off_period")
		time_diff = (
			(frappe.utils.now_datetime() - last_auto_scale_at)
			if last_auto_scale_at
			else timedelta(seconds=cool_off_period + 1)
		)

		running_auto_scale = frappe.db.get_value(
			"Auto Scale Record", {"primary_server": self.name, "status": "Running"}
		)

		if running_auto_scale:
			frappe.throw("Auto scale is already running", frappe.ValidationError)

		if time_diff < timedelta(seconds=cool_off_period or 300):
			frappe.throw(
				f"Please wait for {fmt_timedelta(timedelta(seconds=cool_off_period or 300) - time_diff)} before scaling again",
				frappe.ValidationError,
			)

		active_sites_on_primary = frappe.db.get_value(
			"Site", {"server": self.name, "status": "Active"}, pluck="name"
		)
		active_sites_on_secondary = frappe.db.get_value(
			"Site", {"server": self.secondary_server, "status": "Active"}, pluck="name"
		)

		if not active_sites_on_primary and not active_sites_on_secondary:
			frappe.throw("There are no active sites on this server!", frappe.ValidationError)

		active_deployments = frappe.db.get_value(
			"Bench", {"server": self.name, "status": ("in", ["Installing", "Pending"])}
		)

		if active_deployments:
			frappe.throw(
				"Please wait for all active deployments to complete before scaling the server.",
			)

	@dashboard_whitelist()
	@frappe.whitelist()
	def remove_automated_scaling_triggers(self, triggers: list[str]):
		"""Currently we need to remove both since we can't support scaling up trigger without a scaling down trigger"""
		trigger_filters = {"parent": self.name, "name": ("in", triggers)}
		matching_triggers: list[AutoScaleTriggerRow] = frappe.db.get_values(
			"Auto Scale Trigger", trigger_filters, ["metric", "action"], as_dict=True
		)
		frappe.db.delete("Auto Scale Trigger", trigger_filters)

		for trigger in matching_triggers:
			update_or_delete_prometheus_rule_for_scaling(
				self.name, metric=trigger["metric"], action=trigger["action"]
			)

	@dashboard_whitelist()
	@frappe.whitelist()
	def add_automated_scaling_triggers(
		self, metric: Literal["CPU", "Memory"], action: Literal["Scale Up", "Scale Down"], threshold: float
	):
		"""Configure automated scaling based on cpu loads"""

		if not self.secondary_server:
			frappe.throw("Please setup a secondary server to enable auto scaling", frappe.ValidationError)

		threshold = round(threshold, 2)
		existing_trigger = frappe.db.get_value(
			"Auto Scale Trigger", {"action": action, "parent": self.name, "metric": metric}
		)

		if existing_trigger:
			frappe.db.set_value(
				"Auto Scale Trigger",
				existing_trigger,
				{"action": action, "threshold": threshold, "metric": metric},
			)
		else:
			self.append(
				"auto_scale_trigger",
				{"metric": metric, "threshold": threshold, "action": action},
			)
			self.save()

		create_prometheus_rule_for_scaling(
			self.name,
			metric=metric,
			threshold=threshold,
			action=action,
		)

	@dashboard_whitelist()
	@frappe.whitelist()
	def scale_up(self, is_automatically_triggered: bool = False):
		if self.scaled_up:
			frappe.throw("Server is already scaled up", frappe.ValidationError)

		self.validate_scale()

		auto_scale_record = self._create_auto_scale_record(action="Scale Up")
		auto_scale_record.is_automatically_triggered = is_automatically_triggered
		auto_scale_record.insert()

	@dashboard_whitelist()
	@frappe.whitelist()
	def scale_down(self, is_automatically_triggered: bool = False):
		if not self.scaled_up:
			frappe.throw("Server is already scaled down", frappe.ValidationError)

		self.validate_scale()

		if is_automatically_triggered and not is_secondary_ready_for_scale_down(self):
			return

		auto_scale_record = self._create_auto_scale_record(action="Scale Down")
		auto_scale_record.is_automatically_triggered = is_automatically_triggered
		auto_scale_record.insert()

	@property
	def can_scale(self) -> bool:
		"""
		Check if server is configured for auto scaling
		and all release groups on this server have a password
		"""
		has_release_groups_without_redis_password = bool(
			frappe.db.get_all(
				"Release Group", {"server": self.name, "enabled": 1, "redis_password": ("LIKE", "")}
			)
		)
		return self.benches_on_shared_volume and not has_release_groups_without_redis_password

	def _create_auto_scale_record(self, action: Literal["Scale Up", "Scale Down"]) -> AutoScaleRecord:
		"""Create up/down scale record"""
		return frappe.get_doc({"doctype": "Auto Scale Record", "primary_server": self.name, "action": action})

	@property
	def domains(self):
		filters = {}
		if (
			self.is_self_hosted
		):  # to avoid pushing certificates to self hosted servers on setup_wildcard_hosts
			filters = {"name": self.name}
		return [
			frappe._dict({"domain": domain.name, "code_server": False})
			for domain in frappe.get_all(
				"Root Domain",
				filters={"enabled": 1} | filters,
				fields=["name"],
			)
		]  # To avoid adding child table in server doc


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
		if part:
			abbr += part[0]

	return abbr


def is_dedicated_server(server_name):
	if not isinstance(server_name, str):
		frappe.throw("Invalid argument")
	is_public = frappe.db.get_value("Server", server_name, "public")
	return not is_public
