# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import contextlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import frappe
import frappe.utils
import rq
from frappe.core.doctype.version.version import get_diff
from frappe.core.utils import find
from frappe.utils.password import get_decrypted_password

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
	DatabaseServerMariaDBVariable,
)
from press.press.doctype.server.server import PUBLIC_SERVER_AUTO_ADD_STORAGE_MIN, Agent, BaseServer
from press.runner import Ansible
from press.utils import log_error
from press.utils.database import find_db_disk_info, parse_du_output_of_mysql_directory
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


class DatabaseServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.communication_info.communication_info import CommunicationInfo
		from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
			DatabaseServerMariaDBVariable,
		)
		from press.press.doctype.resource_tag.resource_tag import ResourceTag
		from press.press.doctype.server_mount.server_mount import ServerMount

		agent_password: DF.Password | None
		auto_add_storage_max: DF.Int
		auto_add_storage_min: DF.Int
		auto_increase_storage: DF.Check
		auto_purge_binlog_based_on_size: DF.Check
		bastion_server: DF.Link | None
		binlog_index_retention_days: DF.Int
		binlog_max_disk_usage_percent: DF.Int
		binlog_retention_days: DF.Int
		binlogs_removed: DF.Check
		cluster: DF.Link | None
		communication_info: DF.Table[CommunicationInfo]
		db_port: DF.Int
		domain: DF.Link | None
		enable_binlog_indexing: DF.Check
		enable_binlog_upload_to_s3: DF.Check
		enable_physical_backup: DF.Check
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		gtid_binlog_pos: DF.Data | None
		gtid_current_pos: DF.Data | None
		gtid_slave_pos: DF.Data | None
		halt_agent_jobs: DF.Check
		has_data_volume: DF.Check
		hostname: DF.Data
		hostname_abbreviation: DF.Data | None
		ip: DF.Data | None
		is_binlog_indexer_running: DF.Check
		is_for_recovery: DF.Check
		is_monitoring_disabled: DF.Check
		is_performance_schema_enabled: DF.Check
		is_primary: DF.Check
		is_provisioning_press_job_completed: DF.Check
		is_replication_setup: DF.Check
		is_self_hosted: DF.Check
		is_server_prepared: DF.Check
		is_server_renamed: DF.Check
		is_server_setup: DF.Check
		is_stalk_setup: DF.Check
		is_unified_server: DF.Check
		mariadb_root_password: DF.Password | None
		mariadb_system_variables: DF.Table[DatabaseServerMariaDBVariable]
		memory_allocator: DF.Literal["System", "jemalloc", "TCMalloc"]
		memory_allocator_version: DF.Data | None
		memory_high: DF.Float
		memory_max: DF.Float
		memory_swap_max: DF.Float
		mounts: DF.Table[ServerMount]
		plan: DF.Link | None
		primary: DF.Link | None
		private_ip: DF.Data | None
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI", "Hetzner", "Vodacom", "DigitalOcean"]
		public: DF.Check
		ram: DF.Float
		root_public_key: DF.Code | None
		self_hosted_mariadb_server: DF.Data | None
		self_hosted_server_domain: DF.Data | None
		server_id: DF.Int
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		stalk_cycles: DF.Int
		stalk_function: DF.Data | None
		stalk_gdb_collector: DF.Check
		stalk_interval: DF.Float
		stalk_sleep: DF.Int
		stalk_strace_collector: DF.Check
		stalk_threshold: DF.Int
		stalk_variable: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tags: DF.Table[ResourceTag]
		team: DF.Link | None
		title: DF.Data | None
		tls_certificate_renewal_failed: DF.Check
		uploaded_binlogs_retention_days: DF.Int
		virtual_machine: DF.Link | None
	# end: auto-generated types

	"""
	`dynamic` is used to indicate if the variable can be applied on running server
	For applying non-dynamic variables, we need to restart the server

	---

	`skippable` is used to indicate if the variable is of `skip` type
	skip is to add a `skip_` prefix to the variable.

	It basically enables/disables something.
	Only some variables have it.

	Eg: log_bin . Putting skip_log_bin in config turns off binary logging

	---

	`persist` is to make the variable persist in config file.
	Otherwise, mariadb restart will make config change go away.

	In hindsight, persist should be on by default
	"""

	@property
	def is_part_of_replica(self) -> bool:
		if self.is_replication_setup:
			return True
		return bool(
			self.is_primary
			and frappe.db.exists(
				"Database Server",
				{
					"is_replication_setup": 1,
					"primary": self.name,
				},
			)
		)

	def validate(self):
		super().validate()
		self.validate_mariadb_root_password()
		self.validate_server_id()
		self.validate_server_team()
		self.validate_mariadb_system_variables()
		self.validate_physical_backup()

	def validate_physical_backup(self):
		if self.is_unified_server and self.enable_physical_backup:
			frappe.throw(
				"Physical backup cannot be enabled for unified servers.",
			)

	def validate_mariadb_root_password(self):
		# Check if db server created from snapshot
		if self.is_new() and self.virtual_machine and not self.mariadb_root_password:
			data_disk_snapshot = frappe.get_value(
				"Virtual Machine", self.virtual_machine, "data_disk_snapshot"
			)
			if data_disk_snapshot:
				self.mariadb_root_password = get_decrypted_password(
					"Virtual Disk Snapshot",
					data_disk_snapshot,
					"mariadb_root_password",
				)

		# Generate a random password if not set
		if not self.mariadb_root_password:
			self.mariadb_root_password = frappe.generate_hash(length=32)

	def validate_mariadb_system_variables(self):
		variable: DatabaseServerMariaDBVariable
		for variable in self.mariadb_system_variables:
			variable.validate()

	def validate_server_team(self):
		server_team = frappe.db.get_value(
			"Server", {"database_server": self.name, "status": "Active"}, "team"
		)
		if server_team and self.team != server_team:
			frappe.throw(
				"App server and Database server team must be same.",
				title="Team Change Not Allowed",
			)

	def before_insert(self):
		if self.auto_increase_storage:
			self.auto_purge_binlog_based_on_size = True
			self.binlog_max_disk_usage_percent = 75
		else:
			self.auto_purge_binlog_based_on_size = True
			self.binlog_max_disk_usage_percent = 20

	def on_update(self):
		self.publish_linked_server_realtime_update()

		if self.flags.in_insert or self.is_new():
			return

		if self.is_replication_setup and self.auto_purge_binlog_based_on_size:
			frappe.throw("Cannot enable binlog auto purge for replication configured servers")

		self.update_mariadb_system_variables()
		if (
			self.has_value_changed("memory_high")
			or self.has_value_changed("memory_max")
			or self.has_value_changed("memory_swap_max")
		):
			self.update_memory_limits()

		if not self.is_new() and self.has_value_changed("team"):
			self.update_subscription()

		if self.public:
			self.auto_add_storage_min = max(self.auto_add_storage_min, PUBLIC_SERVER_AUTO_ADD_STORAGE_MIN)

	def publish_linked_server_realtime_update(self):
		with contextlib.suppress(Exception):
			app_server = frappe.db.exists(
				"Server",
				{
					"database_server": self.name,
					"status": ["!=", "Archived"],
				},
			)
			if app_server:
				frappe.publish_realtime(
					"doc_update",
					{
						"doctype": "Server",
						"name": app_server,
					},
					doctype="Server",
					docname=app_server,
					after_commit=True,
				)

	def update_subscription(self):
		if self.subscription:
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
				self.subscription.disable()
			else:
				frappe.db.set_value("Subscription", self.subscription.name, {"team": self.team, "enabled": 1})
		else:
			try:
				# create new subscription
				self.create_subscription(self.plan)
			except Exception:
				frappe.log_error("Database Subscription Creation Error")

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

	def get_doc(self, doc):
		doc = super().get_doc(doc)
		doc.mariadb_variables = {
			"innodb_buffer_pool_size": self.get_mariadb_variable_value(
				"innodb_buffer_pool_size", return_default_if_not_found=True
			),
			"max_connections": frappe.utils.cint(
				self.get_mariadb_variable_value("max_connections", return_default_if_not_found=True)
			),
			"expire_logs_days": frappe.utils.cint(
				self.get_mariadb_variable_value("expire_logs_days", return_default_if_not_found=True)
			),
		}
		doc.mariadb_variables_recommended_values = {
			"innodb_buffer_pool_size": self.recommended_innodb_buffer_pool_size,
			"max_connections": max(50, self.recommended_max_db_connections),
			"expire_logs_days": 14,
		}
		doc.auto_purge_binlog_based_on_size = self.auto_purge_binlog_based_on_size
		doc.binlog_max_disk_usage_percent = self.binlog_max_disk_usage_percent
		return doc

	def get_actions(self):
		server_actions = super().get_actions()

		if self.is_unified_server:
			# Remove rename from database actions section for unified servers
			server_actions = list(
				filter(lambda action: action.get("action") != "Rename server", server_actions)
			)

		server_type = "database server" if not self.is_unified_server else "database"
		actions = [
			{
				"action": "View Database Configuration",
				"description": "View Database Configuration",
				"button_label": "View",
				"condition": self.status == "Active",
				"doc_method": "get_mariadb_variables",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Manage Database Binlogs",
				"description": "View binlogs and purge old binlogs",
				"button_label": "View",
				"condition": self.status == "Active",
				"doc_method": "get_binlogs_info",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Update Binlog Retention",
				"description": "Increase/Decrease Binlog Retention",
				"button_label": "Update",
				"condition": self.status == "Active" and not self.is_replication_setup,
				"doc_method": "update_binlog_retention",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Update Binlog Size Limit",
				"description": "Limit the amount of disk space used by binlogs",
				"button_label": "Update",
				"condition": self.status == "Active" and not self.is_part_of_replica,
				"doc_method": "update_binlog_size_limit",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Enable Binlog Indexer",
				"description": "Start binlog indexer to be able to browse binlogs from dashboard",
				"button_label": "Enable",
				"condition": self.status == "Active" and not self.enable_binlog_indexing and self.ram > 4096,
				"doc_method": "enable_binlog_indexing_service",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Disable Binlog Indexer",
				"description": "Stop binlog indexer to disable browsing binlogs from dashboard",
				"button_label": "Disable",
				"condition": self.status == "Active" and self.enable_binlog_indexing,
				"doc_method": "disable_binlog_indexing_service",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Enable Performance Schema",
				"description": "Activate for enhanced database insights",
				"button_label": "Enable",
				"condition": self.status == "Active" and not self.is_performance_schema_enabled,
				"doc_method": "enable_performance_schema",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Disable Performance Schema",
				"description": "Disable to reduce extra overhead",
				"button_label": "Disable",
				"condition": self.status == "Active" and self.is_performance_schema_enabled,
				"doc_method": "disable_performance_schema",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Update InnoDB Buffer Pool Size",
				"description": "Increase/Decrease InnoDB Buffer Pool Size",
				"button_label": "Update",
				"condition": self.status == "Active",
				"doc_method": "update_innodb_buffer_pool_size",
				"group": f"{server_type.title()} Actions",
			},
			{
				"action": "Update Max DB Connections",
				"description": "Increase/Decrease Max DB Connections",
				"button_label": "Update",
				"condition": self.status == "Active",
				"doc_method": "update_max_db_connections",
				"group": f"{server_type.title()} Actions",
			},
		]

		for action in actions:
			action["server_doctype"] = self.doctype
			action["server_name"] = self.name

		return [action for action in actions if action.get("condition", True)] + server_actions

	def update_memory_limits(self):
		frappe.enqueue_doc(self.doctype, self.name, "_update_memory_limits", enqueue_after_commit=True)

	def _update_memory_limits(self):
		self.memory_swap_max = self.memory_swap_max or 0.1
		if not self.memory_high or not self.memory_max:
			return
		ansible = Ansible(
			playbook="database_memory_limits.yml",
			server=self,
			user=self.ssh_user or "root",
			port=self.ssh_port or 22,
			variables={
				"server": self.name,
				"memory_high": self.memory_high,
				"memory_max": self.memory_max,
				"memory_swap_max": self.memory_swap_max,
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("Database Server Update Memory Limits Error", server=self.name)

	def update_mariadb_system_variables(self):
		variables_to_update = self.get_variables_to_update()
		if not variables_to_update:
			return
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_update_mariadb_system_variables",
			queue="long",
			enqueue_after_commit=True,
			variables=self.get_variables_to_update(),
			now=(
				hasattr(self, "flags")
				and hasattr(self.flags, "update_mariadb_system_variables_synchronously")
				and self.flags.update_mariadb_system_variables_synchronously
			),
		)

	def get_changed_variables(
		self, row_changed: list[tuple[str, int, str, list[tuple]]]
	) -> list[DatabaseServerMariaDBVariable]:
		res = []
		for li in row_changed:
			if li[0] == "mariadb_system_variables":
				values = li[3]
				for value in values:
					if value[1] or value[2]:  # Either value is truthy
						res.append(frappe.get_doc("Database Server MariaDB Variable", li[2]))

		return res

	def get_newly_added_variables(self, added) -> list[DatabaseServerMariaDBVariable]:
		return [
			DatabaseServerMariaDBVariable(row[1].doctype, row[1].name)
			for row in added
			if row[0] == "mariadb_system_variables"
		]

	def get_variables_to_update(self) -> list[DatabaseServerMariaDBVariable]:
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return self.mariadb_system_variables
		diff = get_diff(old_doc, self) or {}
		return self.get_changed_variables(diff.get("row_changed", {})) + self.get_newly_added_variables(
			diff.get("added", [])
		)

	def _update_mariadb_system_variables(self, variables: list[DatabaseServerMariaDBVariable] | None = None):
		if variables is None:
			variables = []
		restart = False
		for variable in variables:
			variable.update_on_server()
			if not variable.dynamic:
				restart = True
		if restart:
			self._restart_mariadb()

	@frappe.whitelist()
	def restart_mariadb(self):
		frappe.enqueue_doc(self.doctype, self.name, "_restart_mariadb")

	def _restart_mariadb(self):
		ansible = Ansible(
			playbook="restart_mysql.yml",
			server=self,
			user=self.ssh_user or "root",
			port=self.ssh_port or 22,
			variables={
				"server": self.name,
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("MariaDB Restart Error", server=self.name)

	@frappe.whitelist()
	def stop_mariadb(self):
		frappe.enqueue_doc(self.doctype, self.name, "_stop_mariadb", timeout=1800)

	def _stop_mariadb(self):
		ansible = Ansible(
			playbook="stop_mariadb.yml",
			server=self,
			user=self.ssh_user or "root",
			port=self.ssh_port or 22,
			variables={
				"server": self.name,
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("MariaDB Stop Error", server=self.name)

	@frappe.whitelist()
	def run_upgrade_mariadb_job(self):
		self.run_press_job("Upgrade MariaDB")

	@frappe.whitelist()
	def upgrade_mariadb(self):
		frappe.enqueue_doc(self.doctype, self.name, "_upgrade_mariadb", timeout=1800)

	def _upgrade_mariadb(self):
		ansible = Ansible(
			playbook="upgrade_mariadb.yml",
			server=self,
			user=self.ssh_user or "root",
			port=self.ssh_port or 22,
			variables={
				"server": self.name,
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("MariaDB Upgrade Error", server=self.name)

	@frappe.whitelist()
	def update_mariadb(self):
		frappe.enqueue_doc(self.doctype, self.name, "_update_mariadb", timeout=1800)

	def _update_mariadb(self):
		ansible = Ansible(
			playbook="update_mariadb.yml",
			server=self,
			user=self.ssh_user or "root",
			port=self.ssh_port or 22,
			variables={
				"server": self.name,
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("MariaDB Update Error", server=self.name)

	@frappe.whitelist()
	def upgrade_mariadb_patched(self):
		frappe.enqueue_doc(self.doctype, self.name, "_upgrade_mariadb_patched", timeout=1800)

	def _upgrade_mariadb_patched(self):
		ansible = Ansible(
			playbook="upgrade_mariadb_patched.yml",
			server=self,
			user=self.ssh_user or "root",
			port=self.ssh_port or 22,
			variables={
				"server": self.name,
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("MariaDB Upgrade Error", server=self.name)

	def add_or_update_mariadb_variable(  # noqa: C901
		self,
		variable: str,
		value_type: Literal["value_int", "value_float", "value_str"],
		value: Any | None = None,
		skip: bool = False,
		persist: bool = True,
		save: bool = True,
		avoid_update_if_exists: bool = False,
		update_variables_synchronously: bool = False,  # This will run the job in same thread
	):
		"""Add or update MariaDB variable on the server"""
		if not skip and not value:
			frappe.throw("For non-skippable variables, value is mandatory")

		self.flags.update_mariadb_system_variables_synchronously = update_variables_synchronously

		existing = find(self.mariadb_system_variables, lambda x: x.mariadb_variable == variable)
		if existing:
			if not avoid_update_if_exists:
				existing.set("skip", skip)
				if not skip:
					existing.set(value_type, value)
				existing.set("persist", persist)
		else:
			data = {
				"mariadb_variable": variable,
				"skip": skip,
				"persist": persist,
			}
			if not skip:
				data.update({value_type: value})

			self.append(
				"mariadb_system_variables",
				data,
			)

		"""
		If it's `performance_schema` variable and set to 1 or ON
		ensure to set other variables if not available
		"""
		if variable == "performance_schema":
			if value in (1, "1", "ON"):
				for key, value in PERFORMANCE_SCHEMA_VARIABLES.items():
					if key == "performance_schema":
						continue

					self.add_or_update_mariadb_variable(
						key, "value_str", value, skip=False, persist=True, avoid_update_if_exists=True
					)

				self.is_performance_schema_enabled = True
			elif value in (0, "0", "OFF"):
				self.is_performance_schema_enabled = False

		if save:
			self.save(ignore_permissions=True)

	@dashboard_whitelist()
	def get_mariadb_variable_value(  # noqa: C901
		self, variable: str, return_default_if_not_found: bool = False
	) -> str | int | float | None:
		existing = find(self.mariadb_system_variables, lambda x: x.mariadb_variable == variable)
		if existing:
			variable_datatype = frappe.db.get_value("MariaDB Variable", existing.mariadb_variable, "datatype")
			if variable_datatype == "Int":
				return existing.value_int
			if variable_datatype == "Float":
				return existing.value_float
			if variable_datatype == "Str":
				return existing.value_str

		if return_default_if_not_found:
			# Ref : https://github.com/frappe/press/blob/master/press/playbooks/roles/mariadb/templates/mariadb.cnf
			match variable:
				case "innodb_buffer_pool_size":
					return int(self.ram_for_mariadb * 0.65)
				case "max_connections":
					return 200
				case "expire_logs_days":
					return 14
		return None

	@dashboard_whitelist()
	def update_innodb_buffer_pool_size(self, size_mb: int):
		# InnoDB need to be at least 20% of RAM
		if size_mb < int(self.ram_for_mariadb * 0.2):
			frappe.throw(f"InnoDB Buffer Size cannot be less than {int(self.ram_for_mariadb * 0.2)}MB.")

		# Hard limit 70% of Memory
		if size_mb > int(self.ram_for_mariadb * 0.70):
			frappe.throw(
				f"InnoDB Buffer Size cannot be greater than {int(self.ram_for_mariadb * 0.70)}MB. If you need larger InnoDB Buffer Size, please increase memory of database server."
			)
		self.add_or_update_mariadb_variable("innodb_buffer_pool_size", "value_int", size_mb, save=True)

	@dashboard_whitelist()
	def update_binlog_retention(self, days: str | int):
		if isinstance(days, str):
			if not days.isdigit():
				frappe.throw("Binlog retention days must be a positive integer")
			days = int(days)
		if days < 1:
			frappe.throw("Binlog retention days cannot be less than 1")

		self.binlog_retention_days = days
		# From MariaDB 10.6.1, expire_logs_days is alias of binlog_expire_logs_seconds
		# https://mariadb.com/docs/server/ha-and-performance/standard-replication/replication-and-binary-log-system-variables#expire_logs_days
		self.add_or_update_mariadb_variable("expire_logs_days", "value_str", str(days), save=True)

	@dashboard_whitelist()
	def update_binlog_size_limit(self, enabled: bool, percent_of_disk_size: int):
		if self.is_part_of_replica:
			frappe.throw("Cannot update binlog size limit for database replicas")

		if percent_of_disk_size is None:
			percent_of_disk_size = 0
		if enabled:
			if percent_of_disk_size < 10 or percent_of_disk_size > 90:
				frappe.throw("Percent of disk space  must be between 10 and 90")
			self.binlog_max_disk_usage_percent = percent_of_disk_size
			self.auto_purge_binlog_based_on_size = True
		else:
			self.auto_purge_binlog_based_on_size = False
			self.binlog_max_disk_usage_percent = 100

		self.save(ignore_permissions=True)

	@dashboard_whitelist()
	def update_max_db_connections(self, max_connections: int):
		max_possible_connections = int(self.ram_for_mariadb / self.memory_per_db_connection)
		if max_connections > max_possible_connections:
			frappe.throw(
				f"Max Connections cannot be greater than {max_possible_connections}. If you need more connections, please increase memory of database server."
			)
		if max_connections < 10:
			frappe.throw("Max Connections cannot be less than 10")

		self.add_or_update_mariadb_variable("max_connections", "value_str", str(max_connections), save=True)

	def validate_server_id(self):
		if self.is_new() and not self.server_id:
			server_ids = frappe.get_all("Database Server", fields=["server_id"], pluck="server_id")
			if server_ids:
				self.server_id = max(server_ids or []) + 1
			else:
				self.server_id = 1

	def _setup_server(self):
		config = self._get_config()
		try:
			ansible = Ansible(
				playbook="self_hosted_db.yml" if getattr(self, "is_self_hosted", False) else "database.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server_type": self.doctype,
					"server": self.name,
					"workers": "2",
					"agent_password": config.agent_password,
					"agent_repository_url": config.agent_repository_url,
					"agent_branch": config.agent_branch,
					"monitoring_password": config.monitoring_password,
					"log_server": config.log_server,
					"kibana_password": config.kibana_password,
					"private_ip": self.private_ip,
					"server_id": self.server_id,
					"allocator": self.memory_allocator.lower(),
					"db_port": self.db_port or 3306,
					"mariadb_root_password": config.mariadb_root_password,
					"certificate_private_key": config.certificate.private_key,
					"certificate_full_chain": config.certificate.full_chain,
					"certificate_intermediate_chain": config.certificate.intermediate_chain,
					"mariadb_depends_on_mounts": self.mariadb_depends_on_mounts,
					**self.get_mount_variables(),
				},
			)
			play = ansible.run()
			self.reload()
			self._set_mount_status(play)
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
				self.process_hybrid_server_setup()
				if self.provider == "DigitalOcean":
					# Adjusting docker permissions
					self.reboot()
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Database Server Setup Exception", server=self.as_dict())
		self.save()

	def _get_config(self):
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)

		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password("kibana_password")
		else:
			kibana_password = None

		return frappe._dict(
			dict(
				agent_password=self.get_password("agent_password"),
				agent_repository_url=self.get_agent_repository_url(),
				agent_branch=self.get_agent_repository_branch(),
				mariadb_root_password=self.get_password("mariadb_root_password"),
				certificate=certificate,
				monitoring_password=frappe.get_doc("Cluster", self.cluster).get_password(
					"monitoring_password"
				),
				log_server=log_server,
				kibana_password=kibana_password,
			)
		)

	def ansible_run(self, command: str) -> dict[str, str]:
		inventory = f"{self.ip},"
		return AnsibleAdHoc(sources=inventory).run(command, self.name)[0]

	@frappe.whitelist()
	def setup_essentials(self):
		"""Setup missing essentials after server setup"""
		config = self._get_config()

		try:
			ansible = Ansible(
				playbook="setup_essentials.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
					"server": self.name,
					"workers": "2",
					"agent_password": config.agent_password,
					"agent_repository_url": config.agent_repository_url,
					"monitoring_password": config.monitoring_password,
					"log_server": config.log_server,
					"kibana_password": config.kibana_password,
					"private_ip": self.private_ip,
					"server_id": self.server_id,
					"certificate_private_key": config.certificate.private_key,
					"certificate_full_chain": config.certificate.full_chain,
					"certificate_intermediate_chain": config.certificate.intermediate_chain,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
		except Exception:
			self.status = "Broken"
			log_error("Setup failed for missing essentials", server=self.as_dict())
		self.save()

	def setup_binlog_indexes_folder(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup_binlog_indexes_folder",
			queue="short",
			timeout=1200,
		)

	def _setup_binlog_indexes_folder(self):
		try:
			ansible = Ansible(
				playbook="setup_binlog_indexes_folder.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Archived folder setup error", server=self.as_dict())

	def setup_user_lingering(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_setup_user_lingering",
			queue="short",
			timeout=1200,
		)

	def _setup_user_lingering(self):
		try:
			ansible = Ansible(
				playbook="setup_user_lingering.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("User lingering setup error", server=self.as_dict())

	def process_hybrid_server_setup(self):
		try:
			hybrid_server = frappe.db.get_value("Self Hosted Server", {"database_server": self.name}, "name")

			if hybrid_server:
				hybrid_server = frappe.get_doc("Self Hosted Server", hybrid_server)

				if not hybrid_server.different_database_server:
					hybrid_server._setup_app_server()
		except Exception:
			log_error("Hybrid Server Setup exception", server=self.as_dict())

	def _setup_primary(self, secondary):
		mariadb_root_password = self.get_password("mariadb_root_password")
		secondary_root_public_key = frappe.db.get_value("Database Server", secondary, "root_public_key")
		try:
			ansible = Ansible(
				playbook="primary.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"backup_path": "/tmp/replica",
					"mariadb_root_password": mariadb_root_password,
					"db_port": self.db_port or 3306,
					"secondary_root_public_key": secondary_root_public_key,
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
		primary = frappe.get_doc("Database Server", self.primary)
		mariadb_root_password = primary.get_password("mariadb_root_password")
		try:
			ansible = Ansible(
				playbook="secondary.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"mariadb_root_password": mariadb_root_password,
					"primary_private_ip": primary.private_ip,
					"primary_ssh_port": primary.ssh_port,
					"private_ip": self.private_ip,
					"db_port": self.db_port or 3306,
					"primary_db_port": primary.db_port or 3306,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_replication_setup = True
				self.mariadb_root_password = mariadb_root_password
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Secondary Server Setup Exception", server=self.as_dict())
		self.save()

	def _setup_replication(self):
		primary = frappe.get_doc("Database Server", self.primary)
		primary._setup_primary(self.name)
		if primary.status == "Active":
			self._setup_secondary()

	@frappe.whitelist()
	def setup_replication(self):
		if self.is_primary:
			return
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_setup_replication", queue="long", timeout=18000)

	@frappe.whitelist()
	def perform_physical_backup(self, path):
		if not path:
			frappe.throw("Provide a path to store the physical backup")
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_perform_physical_backup",
			queue="long",
			timeout=18000,
			path=path,
		)

	def _perform_physical_backup(self, path):
		mariadb_root_password = self.get_password("mariadb_root_password")
		try:
			ansible = Ansible(
				playbook="mariadb_physical_backup.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"mariadb_root_password": mariadb_root_password,
					"backup_path": path,
				},
			)
			ansible.run()
		except Exception:
			log_error("MariaDB Physical Backup Exception", server=self.as_dict())

	def _trigger_failover(self):
		try:
			ansible = Ansible(
				playbook="failover.yml",
				user=self._ssh_user(),
				port=self._ssh_port(),
				server=self,
				variables={"mariadb_root_password": self.get_password("mariadb_root_password")},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_replication_setup = False
				self.is_primary = True
				old_primary = self.primary
				self.primary = None
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Database Server Failover Exception", server=self.as_dict())
		self.save()
		self._update_db_reference_for_app_server(old_primary)

	def _update_db_reference_for_app_server(self, old_primary):
		"""Configure the old primary server after failover"""
		servers = frappe.get_all("Server", {"database_server": old_primary})
		for server in servers:
			server = frappe.get_doc("Server", server.name)
			server.database_server = self.name
			server.save()

	@frappe.whitelist()
	def trigger_failover(self):
		if self.is_primary:
			return
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_trigger_failover", queue="long", timeout=1200)

	def _convert_from_frappe_server(self):
		mariadb_root_password = self.get_password("mariadb_root_password")
		try:
			ansible = Ansible(
				playbook="convert.yml",
				server=self,
				user=self.ssh_user,
				port=self.ssh_port,
				variables={
					"private_ip": self.private_ip,
					"mariadb_root_password": mariadb_root_password,
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
				server = frappe.get_doc("Server", self.name)
				server.database_server = self.name
				server.save()
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Database Server Conversion Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def convert_from_frappe_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(self.doctype, self.name, "_convert_from_frappe_server", queue="long", timeout=1200)

	def _install_exporters(self):
		mariadb_root_password = self.get_password("mariadb_root_password")
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password("monitoring_password")
		try:
			ansible = Ansible(
				playbook="database_exporters.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"private_ip": self.private_ip,
					"mariadb_root_password": mariadb_root_password,
					"monitoring_password": monitoring_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Exporters Install Exception", server=self.as_dict())

	@frappe.whitelist()
	def reset_root_password(self):
		if self.is_primary:
			self.reset_root_password_primary()
		else:
			self.reset_root_password_secondary()

	def reset_root_password_primary(self):
		old_password = self.get_password("mariadb_root_password")
		self.mariadb_root_password = frappe.generate_hash(length=32)
		try:
			ansible = Ansible(
				playbook="mariadb_change_root_password.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"mariadb_old_root_password": old_password,
					"mariadb_root_password": self.mariadb_root_password,
					"private_ip": self.private_ip,
					"db_port": self.db_port or 3306,
				},
			)
			ansible.run()
			self.save()
		except Exception:
			log_error("Database Server Password Reset Exception", server=self.as_dict())
			raise

	def get_replication_status(self):
		return self.agent.get_replication_status(self)

	@frappe.whitelist()
	def sync_replication_config(self):
		data = self.get_replication_status()
		if not data.get("success"):
			frappe.throw(data.get("message", "Failed to fetch replication status"))
		data = data.get("data", {})
		if data.get("gtid_binlog_pos"):
			self.gtid_binlog_pos = data.get("gtid_binlog_pos")
		if data.get("gtid_current_pos"):
			self.gtid_current_pos = data.get("gtid_current_pos")
		if data.get("gtid_slave_pos"):
			self.gtid_slave_pos = data.get("gtid_slave_pos")

		self.save()

	@dashboard_whitelist()
	def enable_performance_schema(self):
		self.add_or_update_mariadb_variable(
			"performance_schema", "value_str", "1", skip=False, persist=True, save=True
		)

	@dashboard_whitelist()
	def disable_performance_schema(self):
		self.add_or_update_mariadb_variable(
			"performance_schema", "value_str", "OFF", skip=False, persist=True, save=True
		)

	def reset_root_password_secondary(self):
		primary = frappe.get_doc("Database Server", self.primary)
		self.mariadb_root_password = primary.get_password("mariadb_root_password")
		try:
			ansible = Ansible(
				playbook="mariadb_change_root_password_secondary.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"mariadb_root_password": self.mariadb_root_password,
					"private_ip": self.private_ip,
					"db_port": self.db_port or 3306,
				},
			)
			ansible.run()
			self.save()
		except Exception:
			log_error("Database Server Password Reset Exception", server=self.as_dict())
			raise

	def prepare_mariadb_replica(self):
		"""
		Use this function only if you are starting a replica from a snapshot of a master server.
		It will prepare the replica by setting up the necessary configurations.
		"""
		frappe.enqueue_doc(
			self.doctype, self.name, "_prepare_mariadb_replica", queue="long", timeout=1200, at_front=True
		)

	def _prepare_mariadb_replica(self):
		if self.is_primary:
			return

		if self.is_replication_setup:
			return

		try:
			ansible = Ansible(
				playbook="mariadb_prepare_replica.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"mariadb_root_password": self.get_password("mariadb_root_password"),
					"private_ip": self.private_ip,
					"mariadb_server_id": self.server_id,
				},
			)
			ansible.run()
		except Exception:
			log_error("MariaDB Prepare Replica Exception", server=self.as_dict())

	def configure_replication(self, gtid_slave_pos: str | None = None):
		if self.is_primary:
			return

		primary_db: "DatabaseServer" = frappe.get_doc("Database Server", self.primary)

		agent = self.agent
		data = agent.configure_replication(
			self,
			primary_db,
			gtid_slave_pos=gtid_slave_pos,
		)
		if not data.get("success"):
			frappe.throw(data.get("message", "Failed to configure replication"))

		if not self.is_replication_setup:
			self.is_replication_setup = True
			self.save()

	def reset_replication(self):
		if self.is_primary:
			return

		agent = self.agent
		data = agent.reset_replication(self)
		if not data.get("success"):
			frappe.throw(data.get("message", "Failed to reset replication"))

		self.is_replication_setup = False
		self.is_primary = True
		self.primary = None
		self.save()

	def start_replication(self):
		if self.is_primary:
			return

		agent = self.agent
		data = agent.start_replication(self)
		if not data.get("success"):
			frappe.throw(data.get("message", "Failed to start replication"))

		self.enable_read_only_mode()

	def stop_replication(self):
		if self.is_primary:
			return

		agent = self.agent
		data = agent.stop_replication(self)
		if not data.get("success"):
			frappe.throw(data.get("message", "Failed to stop replication"))

	@frappe.whitelist()
	def setup_deadlock_logger(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_deadlock_logger", queue="long", timeout=1200)

	def _setup_deadlock_logger(self):
		try:
			ansible = Ansible(
				playbook="deadlock_logger.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"mariadb_root_password": self.get_password("mariadb_root_password"),
					"private_ip": self.private_ip,
				},
			)
			ansible.run()
		except Exception:
			log_error("Deadlock Logger Setup Exception", server=self.as_dict())

	def capture_process_list(self) -> None:
		frappe.enqueue_doc(self.doctype, self.name, "_capture_process_list")

	def _capture_process_list(self) -> str | None:
		"""Capture full process list on the database server"""
		try:
			ansible = Ansible(
				playbook="capture_process_list.yml", server=self, user=self._ssh_user(), port=self._ssh_port()
			)
			play = ansible.run()
			task = frappe.get_doc("Ansible Task", {"play": play.name})
			return task.output
		except Exception:
			log_error("Process List Capture Exception", server=self.as_dict())
			return None

	@frappe.whitelist()
	def setup_pt_stalk(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_pt_stalk", queue="long", timeout=1200)

	def _setup_pt_stalk(self):
		extra_port_variable = find(
			self.mariadb_system_variables, lambda x: x.mariadb_variable == "extra_port"
		)
		if extra_port_variable:
			mariadb_port = extra_port_variable.value_str
		else:
			mariadb_port = 3306
		try:
			ansible = Ansible(
				playbook="pt_stalk.yml",
				server=self,
				variables={
					"private_ip": self.private_ip,
					"mariadb_port": mariadb_port,
					"stalk_function": self.stalk_function,
					"stalk_variable": self.stalk_variable,
					"stalk_threshold": self.stalk_threshold,
					"stalk_sleep": self.stalk_sleep,
					"stalk_cycles": self.stalk_cycles,
					"stalk_interval": self.stalk_interval,
					"stalk_gdb_collector": bool(self.stalk_gdb_collector),
					"stalk_strace_collector": bool(self.stalk_strace_collector),
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.is_stalk_setup = True
				self.save()
		except Exception:
			log_error("Percona Stalk Setup Exception", server=self.as_dict())

	def _setup_logrotate(self):
		try:
			ansible = Ansible(
				playbook="rotate_mariadb_logs.yml", server=self, user=self._ssh_user(), port=self._ssh_port()
			)
			ansible.run()
		except Exception:
			log_error("Logrotate Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def provide_frappe_user_du_and_find_permission(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_provide_frappe_user_du_and_find_permission", queue="long", timeout=1200
		)

	def _provide_frappe_user_du_and_find_permission(self):
		try:
			ansible = Ansible(
				playbook="provide_frappe_user_du_and_find_permission.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("MariaDB Provide Frappe User DU Permission Exception", server=self.as_dict())

	@frappe.whitelist()
	def provide_frappe_user_mariadb_table_usage_permission(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_provide_frappe_user_mariadb_table_usage_permission",
			queue="long",
			timeout=1200,
		)

	def _provide_frappe_user_mariadb_table_usage_permission(self):
		try:
			ansible = Ansible(
				playbook="provide_frappe_user_mariadb_table_usage_permission.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error(
				"MariaDB Provide Frappe User Mariadb Table Usage Permission Exception", server=self.as_dict()
			)

	@frappe.whitelist()
	def setup_mariadb_debug_symbols(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_mariadb_debug_symbols", queue="long", timeout=1200
		)

	def _setup_mariadb_debug_symbols(self):
		try:
			ansible = Ansible(
				playbook="mariadb_debug_symbols.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("MariaDB Debug Symbols Setup Exception", server=self.as_dict())

	@frappe.whitelist()
	def fetch_stalks(self):
		frappe.enqueue(
			"press.press.doctype.mariadb_stalk.mariadb_stalk.fetch_server_stalks",
			server=self.name,
			job_id=f"fetch_mariadb_stalk:{self.name}",
			deduplicate=True,
			queue="long",
		)

	def get_stalks(self):
		if self.agent.should_skip_requests():
			return []
		result = self.agent.get("database/stalks", raises=False)
		if (not result) or ("error" in result):
			return []
		return result

	def get_stalk(self, name):
		if self.agent.should_skip_requests():
			return {}
		return self.agent.get(f"database/stalks/{name}")

	def _rename_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		mariadb_root_password = self.get_password("mariadb_root_password")
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
				playbook="database_rename.yml",
				server=self,
				variables={
					"server_type": self.doctype,
					"server": self.name,
					"workers": "2",
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"monitoring_password": monitoring_password,
					"log_server": log_server,
					"kibana_password": kibana_password,
					"private_ip": self.private_ip,
					"server_id": self.server_id,
					"mariadb_root_password": mariadb_root_password,
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
			log_error("Database Server Rename Exception", server=self.as_dict())
		self.save()

	system_reserved_memory: int = 700
	"""
	OS : 500 MB
	Agent + Redis Server : ~100 MB
	Filebeat : ~100 MB
	"""

	memory_per_db_connection: int = 35
	"""
	Per DB Connection Memory : ~35MB
	- sort_buffer_size : 2MB
	- read_buffer_size : 0.13MB
	- read_rnd_buffer_size : 0.26MB
	- join_buffer_size : 0.26MB
	- thread_stack : 0.29MB
	- binlog_cache_size : 0.03MB
	- max_heap_table_size : 32MB

	https://github.com/frappe/press/blob/master/press/playbooks/roles/mariadb/templates/mariadb.cnf
	"""

	@property
	def key_buffer_size(self):
		"""
		key-buffer-size :
		- If server has 4GB Ram, set to 32MB (Default set by press)
		- Else set to 128MB

		Database Server should have 1:100 ratio for Key Reads and Key Read Requests on MyISAM tables
		"""
		if self.ram_for_mariadb > 4096:
			return 128

		return 32

	@property
	def base_memory_mariadb(self):
		"""
		Base Memory
		- key_buffer_size +
		- query_cache_size : 0MB
		- tmp_table_size : 32MB (applies to internal temporary tables created during query execution)
		- innodb_log_buffer_size : 16MB

		https://github.com/frappe/press/blob/master/press/playbooks/roles/mariadb/templates/mariadb.cnf
		"""
		return self.key_buffer_size + 32 + 16

	@property
	def recommended_max_db_connections(self):
		"""
		Based on historical data, the simple formula for recommending max_connections is:
		5 DB Users per GB of RAM

		e.g. For 4GB of server, this will be 20

		But, set lower bound of 50 connections
		"""
		return 5 * round(self.ram / 1024)

	@property
	def ram_for_mariadb(self):
		return self.real_ram - self.system_reserved_memory

	@property
	def recommended_innodb_buffer_pool_size(self):
		return min(
			int(
				self.ram_for_mariadb
				- self.base_memory_mariadb
				- self.recommended_max_db_connections * self.memory_per_db_connection
			),
			int(self.ram_for_mariadb * 0.65),
		)

	@frappe.whitelist()
	def adjust_memory_config(self):  # noqa: C901
		if not self.ram:
			return

		self.memory_high = round(max(self.ram_for_mariadb / 1024 - 1, 1), 3)
		self.memory_max = round(max(self.ram_for_mariadb / 1024, 2), 3)

		max_recommended_connections = max(50, self.recommended_max_db_connections)
		# Check if we can add some extra connections
		if self.recommended_innodb_buffer_pool_size < int(self.ram_for_mariadb * 0.65):
			extra_connections = round(
				(self.recommended_innodb_buffer_pool_size - int(self.ram_for_mariadb * 0.65))
				/ self.memory_per_db_connection
			)
			max_recommended_connections += extra_connections

		self.add_or_update_mariadb_variable(
			"innodb_buffer_pool_size",
			"value_int",
			self.recommended_innodb_buffer_pool_size,
			save=False,
		)

		existing_max_connections = frappe.utils.cint(self.get_mariadb_variable_value("max_connections"))
		if existing_max_connections is None:
			existing_max_connections = 0

		# Avoid setting max_connections to a lower value, if it's already set to a higher value
		# User might have changed the value in the past, and we don't want to override it
		if max_recommended_connections > existing_max_connections:
			self.add_or_update_mariadb_variable(
				"max_connections", "value_str", str(max_recommended_connections), save=False
			)
		self.add_or_update_mariadb_variable("key_buffer_size", "value_int", self.key_buffer_size, save=False)

		# Recommended Log file size
		# Ref: https://www.percona.com/blog/mysql-8-0-innodb_dedicated_server-variable-optimizes-innodb/
		ram_gb = round(self.ram / 1024)

		if ram_gb > 16:
			log_file_size = 2048
		elif ram_gb > 8:
			log_file_size = 1024
		elif ram_gb > 4:
			log_file_size = 512
		elif ram_gb > 2:
			log_file_size = 128
		else:
			log_file_size = 48
		self.add_or_update_mariadb_variable("innodb_log_file_size", "value_int", log_file_size, save=False)

		self.save(ignore_permissions=True)

	def set_innodb_force_recovery(self, value: int):
		"""Set innodb_force_recovery to the given value"""
		if value < 0 or value > 6:
			frappe.throw("innodb_force_recovery value must be between 0 and 6")
		self.add_or_update_mariadb_variable(
			"innodb_force_recovery", "value_str", str(value), skip=False, persist=True, save=True
		)

	@frappe.whitelist()
	def toggle_read_only_mode(self):
		read_only_mode_value = self.get_mariadb_variable_value("read_only", return_default_if_not_found=True)
		read_only_mode_enabled = read_only_mode_value in (1, "1", "ON")

		if read_only_mode_enabled:
			self.disable_read_only_mode()
		else:
			self.enable_read_only_mode()

	@frappe.whitelist()
	def enable_read_only_mode(self, update_variables_synchronously: bool = False):
		"""Enable read-only mode for the database server"""
		self.add_or_update_mariadb_variable(
			"read_only",
			"value_str",
			"1",
			skip=False,
			persist=True,
			save=True,
			update_variables_synchronously=update_variables_synchronously,
		)

	@frappe.whitelist()
	def disable_read_only_mode(self, update_variables_synchronously: bool = False):
		"""Disable read-only mode for the database server"""
		self.add_or_update_mariadb_variable(
			"read_only",
			"value_str",
			"0",
			skip=False,
			persist=True,
			save=True,
			update_variables_synchronously=update_variables_synchronously,
		)

	@frappe.whitelist()
	def reconfigure_mariadb_exporter(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_reconfigure_mariadb_exporter", queue="long", timeout=1200
		)

	def _reconfigure_mariadb_exporter(self):
		mariadb_root_password = self.get_password("mariadb_root_password")
		try:
			ansible = Ansible(
				playbook="reconfigure_mysqld_exporter.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"private_ip": self.private_ip,
					"mariadb_root_password": mariadb_root_password,
				},
			)
			ansible.run()
		except Exception:
			log_error("Database Server MariaDB Exporter Reconfigure Exception", server=self.as_dict())

	@frappe.whitelist()
	def update_memory_allocator(self, memory_allocator):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_update_memory_allocator",
			memory_allocator=memory_allocator,
			enqueue_after_commit=True,
		)

	def _update_memory_allocator(self, memory_allocator):
		ansible = Ansible(
			playbook="mariadb_memory_allocator.yml",
			server=self,
			user=self._ssh_user(),
			port=self._ssh_port(),
			variables={
				"server": self.name,
				"allocator": memory_allocator.lower(),
				"mariadb_root_password": self.get_password("mariadb_root_password"),
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("MariaDB Memory Allocator Setup Error", server=self.name)
		elif play.status == "Success":
			result = json.loads(
				frappe.get_all(
					"Ansible Task",
					filters={"play": play.name, "task": "Show Memory Allocator"},
					pluck="result",
					order_by="creation DESC",
					limit=1,
				)[0]
			)
			query_result = result.get("query_result")
			if query_result:
				self.reload()
				self.memory_allocator = memory_allocator
				self.memory_allocator_version = query_result[0][0]["Value"]
				self.save()

	@dashboard_whitelist()
	def get_mariadb_variables(self):
		try:
			agent = Agent(self.name, "Database Server")
			return agent.fetch_database_variables()
		except Exception:
			frappe.throw("Failed to fetch MariaDB Variables. Please try again.")

	@property
	def mariadb_depends_on_mounts(self):
		mount_points = set(mount.mount_point for mount in self.mounts)
		mariadb_mount_points = set(["/var/lib/mysql", "/etc/mysql"])
		return mariadb_mount_points.issubset(mount_points)

	def get_binlogs_raw_data(self):
		if self.agent.should_skip_requests():
			frappe.throw("Server is not reachable. Please try again later.")
		return self.agent.fetch_binlog_list()

	@dashboard_whitelist()
	def get_binlogs_info(self):
		data = self.get_binlogs_raw_data()
		binlogs = data.get("binlogs_in_disk", [])
		current_binlog = data.get("current_binlog", "")
		for binlog in binlogs:
			binlog["modified_at"] = datetime.fromtimestamp(int(binlog["modified_at"]))
			binlog["size_mb"] = round((binlog.get("size", 0) / 1024 / 1024), 1)

		# sort by modified_at
		binlogs = sorted(binlogs, key=lambda x: x["modified_at"], reverse=True)
		return [binlog for binlog in binlogs if binlog.get("name") != current_binlog]

	@frappe.whitelist()
	def get_binlog_summary(self):
		binlogs_in_disk = self.get_binlogs_raw_data().get("binlogs_in_disk", [])
		no_of_binlogs = len(binlogs_in_disk)
		size = sum(binlog.get("size", 0) for binlog in binlogs_in_disk)
		size_gb = round(size / 1024 / 1024 / 1024, 1)

		oldest_binlog = binlogs_in_disk[0] if no_of_binlogs > 0 else {}
		latest_binlog = binlogs_in_disk[-1] if no_of_binlogs > 0 else {}
		first_binlog_date = (
			datetime.fromtimestamp(int(oldest_binlog.get("modified_at", 0))) if oldest_binlog else ""
		)
		last_binlog_date = (
			datetime.fromtimestamp(int(latest_binlog.get("modified_at", 0))) if no_of_binlogs > 0 else ""
		)
		first_binlog_size_mb = round(oldest_binlog.get("size", 0) / 1024 / 1024, 1) if oldest_binlog else 0
		last_binlog_size_mb = round(latest_binlog.get("size", 0) / 1024 / 1024, 1) if no_of_binlogs > 0 else 0

		message = f"""No of binlogs in Disk : {no_of_binlogs}<br>
Total size : {size_gb} GB<br><br>
Oldest binlog : {oldest_binlog.get("name", "")} - {first_binlog_size_mb} MB - {first_binlog_date}<br>
Latest binlog : {latest_binlog.get("name", "")} - {last_binlog_size_mb} MB {last_binlog_date}
		"""
		frappe.msgprint(message, "Binlog Summary")

	@dashboard_whitelist()
	def get_binlogs_indexing_status(self):
		if not self.enable_binlog_indexing:
			frappe.throw("Binlog Indexing is not enabled for this server.")

		data = frappe.db.get_all(
			"MariaDB Binlog",
			filters={"database_server": self.name, "purged_from_disk": False},
			fields=[
				"file_name",
				"indexed",
				"size_mb",
				"file_modification_time",
			],
			order_by="file_modification_time DESC",
			limit_page_length=2000,
		)
		# Replace file_name with name
		return [
			{
				"name": row["file_name"],
				"indexed": row["indexed"],
				"size_mb": row["size_mb"],
				"file_modification_time": row["file_modification_time"],
			}
			for row in data
		]

	@dashboard_whitelist()
	def purge_binlogs(self, to_binlog: str):
		"""
		!!!NOTE!!!
		This will purge binlogs from disk.
		to_binlog and older binlogs will be purged.
		"""
		try:
			binlogs_in_disk = [r["name"] for r in self.get_binlogs_raw_data().get("binlogs_in_disk", [])]
			prefix = to_binlog.split(".")[0] + "."
			new_binlog_than_requested = prefix + str(int(to_binlog.split(".")[-1]) + 1).zfill(6)
			if new_binlog_than_requested not in binlogs_in_disk:
				return

			self.agent.purge_binlog(database_server=self, to_binlog=new_binlog_than_requested)
			frappe.msgprint(f"Purged to {to_binlog}", "Successfully purged binlogs")
			if self.enable_binlog_indexing:
				self.sync_binlogs_info(index_binlogs=False, upload_binlogs=False)
		except Exception as e:
			frappe.throw(f"Failed to purge binlogs. Please try again later. {e!s}")
			raise e

	def purge_binlogs_by_configured_size_limit(self):
		if not self.auto_purge_binlog_based_on_size:
			return

		if not self.binlog_max_disk_usage_percent:
			return

		if not self.virtual_machine:
			return

		if self.is_part_of_replica:
			return

		disk_size = frappe.get_value("Virtual Machine", self.virtual_machine, "disk_size")
		binlog_limit_in_gb = int(self.binlog_max_disk_usage_percent / 100 * disk_size)
		if binlog_limit_in_gb == 0:
			return

		self.agent.purge_binlogs_by_size_limit(self, max_binlog_gb=binlog_limit_in_gb)

	@dashboard_whitelist()
	def enable_binlog_indexing_service(self):
		if self.enable_binlog_indexing:
			return

		self.enable_binlog_indexing = True
		self.save(ignore_permissions=True)

	@dashboard_whitelist()
	def disable_binlog_indexing_service(self):
		if not self.enable_binlog_indexing:
			return

		self.enable_binlog_indexing = False
		self.save(ignore_permissions=True)
		frappe.db.set_value(
			"MariaDB Binlog",
			{"database_server": self.name},
			"indexed",
			0,
		)
		frappe.msgprint("Binlog Indexing has been disabled")

	@dashboard_whitelist()
	def sync_binlogs_info(self, index_binlogs: bool = True, upload_binlogs: bool = True):
		if not self.enable_binlog_indexing:
			frappe.msgprint("Binlog Indexing is not enabled")
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_sync_binlogs_info",
			timeout=600,
			upload_binlogs=upload_binlogs,
			index_binlogs=index_binlogs,
		)

	def _sync_binlogs_info(self, index_binlogs: bool = True, upload_binlogs: bool = True):
		info = self.agent.fetch_binlog_list()
		current_binlog = info.get("current_binlog", "")
		binlogs_in_disk = info.get("binlogs_in_disk", [])
		indexed_binlogs = info.get("indexed_binlogs", [])

		# Update entry for binlogs stored in disk
		for binlog in binlogs_in_disk:
			binlog["is_indexed"] = binlog["name"] in indexed_binlogs

			size_mb = round((binlog.get("size", 0) / 1024 / 1024), 1)
			file_modification_time = datetime.fromtimestamp(int(binlog["modified_at"]))

			if not frappe.db.exists(
				"MariaDB Binlog",
				{
					"database_server": self.name,
					"file_name": binlog["name"],
				},
			):
				frappe.get_doc(
					{
						"doctype": "MariaDB Binlog",
						"database_server": self.name,
						"file_name": binlog["name"],
						"size_mb": size_mb,
						"is_indexed": binlog["is_indexed"],
						"purged_from_disk": False,
						"file_modification_time": file_modification_time,
					}
				).insert(ignore_permissions=True)
			else:
				frappe.db.set_value(
					"MariaDB Binlog",
					{
						"database_server": self.name,
						"file_name": binlog["name"],
					},
					{
						"size_mb": size_mb,
						"file_modification_time": file_modification_time,
					},
				)

		# Update entry for current binlog
		current_binlog_set_to = frappe.db.exists(
			"MariaDB Binlog", {"database_server": self.name, "current": True}
		)
		if current_binlog_set_to != current_binlog:
			if current_binlog_set_to:
				frappe.db.set_value(
					"MariaDB Binlog",
					current_binlog_set_to,
					"current",
					0,
				)
			frappe.db.set_value(
				"MariaDB Binlog",
				{"database_server": self.name, "file_name": current_binlog},
				"current",
				1,
			)

		# Set purged_from_disk to True for binlogs that are not in disk
		binlog_file_names_stored_in_disk = [x.get("name") for x in binlogs_in_disk]
		frappe.db.set_value(
			"MariaDB Binlog",
			{
				"database_server": self.name,
				"file_name": ("not in", binlog_file_names_stored_in_disk),
				"purged_from_disk": 0,
			},
			"purged_from_disk",
			1,
		)

		# Set binlogs as indexed
		frappe.db.set_value(
			"MariaDB Binlog",
			{
				"database_server": self.name,
				"file_name": ("in", indexed_binlogs),
			},
			"indexed",
			1,
		)

		# Set other binlogs as non indexed
		frappe.db.set_value(
			"MariaDB Binlog",
			{
				"database_server": self.name,
				"file_name": ("not in", indexed_binlogs),
			},
			"indexed",
			0,
		)

		if index_binlogs:
			self.add_binlogs_to_indexer()

		if upload_binlogs:
			self.upload_binlogs_to_s3()

	def add_binlogs_to_indexer(self):
		if not self.enable_binlog_indexing:
			return

		# Avoid if there is already Binlog Indexing related job
		if self._is_binlog_indexing_related_operation_running():
			return

		"""
		Start indexing from old ones
		Only try to index last 7 days of binlogs
		"""

		binlogs = frappe.get_all(
			"MariaDB Binlog",
			filters={
				"database_server": self.name,
				"indexed": 0,
				"purged_from_disk": 0,
				"file_modification_time": (
					">=",
					frappe.utils.add_to_date(None, days=-1 * 7),
				),
			},
			order_by="file_name asc",
			limit=4,
			fields=["file_name", "size_mb"],
		)

		current_indexed_binlog = frappe.get_all(
			"MariaDB Binlog",
			filters={
				"database_server": self.name,
				"current": 1,
				"indexed": 1,
				"purged_from_disk": 0,
			},
			fields=["file_name", "size_mb"],
		)

		if len(current_indexed_binlog) != 0:
			binlogs.extend(current_indexed_binlog)
			binlogs = sorted(binlogs, key=lambda x: x["file_name"])

		max_size_in_batch = 400
		filtered_binlogs = []
		while max_size_in_batch > 0 and binlogs:
			filtered_binlogs.append(binlogs.pop(0))
			max_size_in_batch -= filtered_binlogs[-1].size_mb

		if len(filtered_binlogs) == 0:
			return

		self.agent.add_binlogs_to_indexer([x["file_name"] for x in filtered_binlogs])

	@dashboard_whitelist()
	def index_binlogs_on_demand(self, binlog_file_names: list[str]):
		if not binlog_file_names:
			return None

		if not self.enable_binlog_indexing:
			frappe.throw("Binlog Indexing is not enabled for this server.")

		if self._is_binlog_indexing_related_operation_running() or self.is_binlog_indexer_running:
			frappe.throw("Another Binlog Indexing related operation is already in progress.")

		job = self.agent.add_binlogs_to_indexer(binlog_file_names)
		return job.name

	def remove_binlogs_from_indexer(self):
		if not self.enable_binlog_indexing:
			return

		# Avoid if there is already Binlog Indexing related job
		if self._is_binlog_indexing_related_operation_running():
			return

		# Fetch indexed binlogs before X days
		binlogs = frappe.get_all(
			"MariaDB Binlog",
			filters={
				"database_server": self.name,
				"indexed": 1,
				"file_modification_time": (
					"<",
					frappe.utils.add_to_date(None, days=-1 * self.binlog_index_retention_days),
				),
			},
			pluck="file_name",
			order_by="file_modification_time asc",
		)
		if len(binlogs) == 0:
			return

		# Ensure that we don't miss any binlogs in between while unindexing
		# If mysql-bin.000001, mysql-bin.000002, mysql-bin.000004 are there,
		# But, mysql-bin.000003 is not indexed, then include that as well in the list

		# Binlog file format mysql-bin.xxxxxxx
		no_of_digits = len(binlogs[0].split(".")[-1])
		first_binlog_no = int(binlogs[0].split(".")[-1])
		last_binlog_no = int(binlogs[-1].split(".")[-1])

		# Generate series of binlog
		unindexable_binlogs = []
		for binlog_no in range(first_binlog_no, last_binlog_no + 1):
			binlog_no_z_filled = str(binlog_no).zfill(no_of_digits)
			unindexable_binlogs.append(f"mysql-bin.{binlog_no_z_filled}")

		self.agent.remove_binlogs_from_indexer(unindexable_binlogs)

	def _is_binlog_indexing_related_operation_running(self):
		if self.is_binlog_indexer_running:
			return True

		return frappe.db.exists(
			"Agent Job",
			{
				"job_type": ("in", ["Add Binlogs to Indexer", "Remove Binlogs From Indexer"]),
				"server": self.name,
				"status": ("in", ["Pending", "Running"]),
			},
		)

	def upload_binlogs_to_s3(self):
		if not self.enable_binlog_indexing or not self.enable_binlog_upload_to_s3:
			return

		# Upload only those binlogs which is indexed
		binlogs = frappe.get_all(
			"MariaDB Binlog",
			filters={"database_server": self.name, "current": 0, "uploaded": 0, "purged_from_disk": 0},
			order_by="file_name asc",
			pluck="file_name",
			limit=5,
		)

		if len(binlogs) == 0:
			return

		self.agent.upload_binlogs_to_s3(binlogs)

	def remove_uploaded_binlogs_from_disk(self):
		# Remove only those binlogs in disk
		binlogs = frappe.get_all(
			"MariaDB Binlog",
			filters={
				"database_server": self.name,
				"current": 0,
				"purged_from_disk": 0,
				"file_modification_time": (
					"<",
					frappe.utils.add_to_date(None, days=self.binlog_retention_days * -1),
				),
			},
			order_by="file_name asc",
			fields=["file_name", "uploaded"],
		)

		to_binlog = None
		for binlog in binlogs:
			if binlog.uploaded:
				to_binlog = binlog.file_name
			else:
				break

		self.purge_binlogs(to_binlog=to_binlog)

	def remove_uploaded_binlogs_from_s3(self):
		# Remove only those binlogs in S3
		binlogs = frappe.get_all(
			"MariaDB Binlog",
			filters={
				"database_server": self.name,
				"current": 0,
				"uploaded": 1,
				"file_modification_time": (
					"<",
					frappe.utils.add_to_date(None, days=-1 * self.uploaded_binlogs_retention_days),
				),
			},
			pluck="name",
		)

		if len(binlogs) == 0:
			return

		for binlog in binlogs:
			frappe.get_doc("MariaDB Binlog", binlog).delete_remote_file()
			frappe.db.commit()

	def delete_all_mariadb_binlog_records(self):
		frappe.enqueue_doc(
			"Database Server",
			self.name,
			"delete_all_mariadb_binlog_records",
			enqueue_after_commit=True,
			queue="long",
			job_id=f"delete_mariadb_binlog_records||{self.name}",
			deduplicate=True,
		)

	def _delete_all_mariadb_binlog_records(self):
		"""
		Delete all binlog records for a server
		"""
		binlogs = frappe.get_all(
			"MariaDB Binlog",
			filters={"database_server": self.name},
			pluck="name",
		)
		if not binlogs:
			return
		for binlog in binlogs:
			frappe.delete_doc("MariaDB Binlog", binlog)
		self.binlogs_removed = 1
		self.save()

	@dashboard_whitelist()
	def get_storage_usage(self):
		try:
			result = AnsibleAdHoc(sources=f"{self.ip},").run(
				'df --output=source,size,used,target | tail -n +2  && echo -e "\n\n" && du -s /var/lib/mysql/*',
				self.name,
				raw_params=True,
			)[0]
			if result.get("status") != "Success":
				raise Exception("Failed to fetch storage usage")

			binlog_indexes_size = 0
			with contextlib.suppress(Exception):
				binlog_indexes_size_result = AnsibleAdHoc(sources=f"{self.ip},").run(
					"du -sk /home/frappe/binlog_indexes/ | cut -f1",
					self.name,
					raw_params=True,
				)[0]
				if binlog_indexes_size_result.get("status") == "Success":
					binlog_indexes_size = int(binlog_indexes_size_result.get("output", "0").strip())

			disk_info_str, mysql_dir_info_str = result.get("output", "\n\n").split("\n\n", 1)
			disk_info = find_db_disk_info(disk_info_str)
			if disk_info is None:
				raise Exception("Failed to parse disk info")

			mysql_storage_info = parse_du_output_of_mysql_directory(mysql_dir_info_str)
			total_db_usage = (
				sum(mysql_storage_info["schema"].values())
				+ mysql_storage_info["bin_log"]
				+ mysql_storage_info["slow_log"]
				+ mysql_storage_info["error_log"]
				+ mysql_storage_info["core"]
				+ mysql_storage_info["other"]
				+ binlog_indexes_size
			)

			sites_db_name_info = frappe.get_all(
				"Site",
				filters={
					"database_name": ("in", mysql_storage_info["schema"].keys()),
				},
				fields=["name", "database_name"],
			)

			db_name_site_mapping = {}
			for site in sites_db_name_info:
				db_name_site_mapping[site.database_name] = site.name

			return {
				"disk_total": disk_info[0],
				"disk_used": disk_info[1],
				"disk_free": disk_info[0] - disk_info[1],
				"database_usage": total_db_usage,
				"binlog_indexes": binlog_indexes_size,
				"os_usage": disk_info[1] - total_db_usage,
				"database": mysql_storage_info,
				"db_name_site_map": db_name_site_mapping,
			}
		except Exception:
			frappe.throw("Failed to fetch storage usage. Try again later.")

	def set_mariadb_mount_dependency(self, now: bool | None = None):
		if not self.mariadb_depends_on_mounts:
			return
		frappe.enqueue_doc(self.doctype, self.name, "_set_mariadb_mount_dependency", timeout=1800, now=now)

	def _set_mariadb_mount_dependency(self):
		try:
			ansible = Ansible(
				playbook="set_mariadb_mount_dependency.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Set MariaDB Mount Dependency Exception", server=self.as_dict())

	@frappe.whitelist()
	def update_database_schema_sizes(self):
		self.agent.update_database_schema_sizes()


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Database Server")

PERFORMANCE_SCHEMA_VARIABLES = {
	"performance_schema": "1",
	"performance-schema-instrument": "'%=ON'",
	"performance-schema-consumer-events-stages-current": "ON",
	"performance-schema-consumer-events-stages-history": "ON",
	"performance-schema-consumer-events-stages-history-long": "ON",
	"performance-schema-consumer-events-statements-current": "ON",
	"performance-schema-consumer-events-statements-history": "ON",
	"performance-schema-consumer-events-statements-history-long": "ON",
	"performance-schema-consumer-events-waits-current": "ON",
	"performance-schema-consumer-events-waits-history": "ON",
	"performance-schema-consumer-events-waits-history-long": "ON",
}


def monitor_disk_performance():
	databases = frappe.db.get_all(
		"Database Server",
		filters={"status": "Active", "is_server_setup": 1, "is_self_hosted": 0},
		pluck="name",
	)
	frappe.enqueue(
		"press.press.doctype.disk_performance.disk_performance.check_disk_read_write_latency",
		servers=databases,
		server_type="db",
		deduplicate=True,
		queue="long",
		job_id="monitor_disk_performance||database",
		timeout=3600,
	)


def sync_binlogs_info():
	if frappe.db.get_single_value("Press Settings", "disable_binlog_indexer_service"):
		return

	databases = frappe.db.get_all(
		"Database Server",
		filters={"status": "Active", "is_server_setup": 1, "is_self_hosted": 0, "enable_binlog_indexing": 1},
		pluck="name",
	)
	for database in databases:
		frappe.enqueue_doc(
			"Database Server",
			database,
			"_sync_binlogs_info",
			job_id=f"sync_binlogs_info:{database}",
			deduplicate=True,
			queue="sync",
		)


def remove_uploaded_binlogs_from_disk():
	if frappe.db.get_single_value("Press Settings", "disable_binlog_indexer_service"):
		return

	databases = frappe.db.get_all(
		"Database Server",
		filters={"status": "Active", "is_server_setup": 1, "is_self_hosted": 0, "enable_binlog_indexing": 1},
		pluck="name",
	)
	for database in databases:
		frappe.enqueue_doc(
			"Database Server",
			database,
			"remove_uploaded_binlogs_from_disk",
			job_id=f"remove_uploaded_binlogs_from_disk:{database}",
			deduplicate=True,
			queue="sync",
		)


def remove_uploaded_binlogs_from_s3():
	if frappe.db.get_single_value("Press Settings", "disable_binlog_indexer_service"):
		return

	databases = frappe.db.get_all(
		"Database Server",
		filters={"status": "Active", "is_server_setup": 1, "is_self_hosted": 0, "enable_binlog_indexing": 1},
		pluck="name",
	)
	for database in databases:
		frappe.enqueue_doc(
			"Database Server",
			database,
			"remove_uploaded_binlogs_from_s3",
			job_id=f"remove_uploaded_binlogs_from_s3:{database}",
			deduplicate=True,
			queue="sync",
		)


def delete_mariadb_binlog_for_archived_servers():
	if frappe.db.get_single_value("Press Settings", "disable_binlog_indexer_service"):
		return
	"""
	Delete binlog records for archived servers
	"""
	archived_servers = frappe.get_all(
		"MariaDB Server",
		filters={"status": "Archived", "binlogs_removed": 0},
		pluck="name",
	)
	if not archived_servers:
		return

	for server in archived_servers:
		frappe.enqueue_doc(
			"Database Server",
			server,
			"delete_all_mariadb_binlog_records",
			enqueue_after_commit=True,
			queue="long",
			job_id=f"delete_mariadb_binlog_records||{server}",
			deduplicate=True,
		)


def unindex_mariadb_binlogs():
	if frappe.db.get_single_value("Press Settings", "disable_binlog_indexer_service"):
		return
	databases = frappe.get_all(
		"Database Server",
		fields=["name"],
		filters={"status": "Active", "is_server_setup": 1, "is_self_hosted": 0, "enable_binlog_indexing": 1},
	)
	for database in databases:
		frappe.get_doc("Database Server", database).remove_binlogs_from_indexer()


def update_binlog_indexer_status_on_agent_job_update(job: AgentJob):
	if not (job.server_type == "Database Server" and job.server):
		return

	if job.status in ["Success", "Failure"]:
		frappe.db.set_value(
			job.server_type, job.server, "is_binlog_indexer_running", False, update_modified=False
		)
	elif job.status in ["Pending", "Running"]:
		frappe.db.set_value(
			job.server_type, job.server, "is_binlog_indexer_running", True, update_modified=False
		)


def process_add_binlogs_to_indexer_agent_job_update(job: AgentJob):
	update_binlog_indexer_status_on_agent_job_update(job)

	if job.status != "Success":
		return

	json_data = json.loads(job.data)
	indexed_binlogs = json_data.get("indexed_binlogs", [])
	frappe.db.set_value(
		"MariaDB Binlog",
		{
			"database_server": job.server,
			"file_name": ("in", indexed_binlogs),
		},
		"indexed",
		1,
	)
	current_binlog_set_to = frappe.db.exists(
		"MariaDB Binlog", {"database_server": job.server, "current": True}
	)
	if current_binlog_set_to != json_data.get("current_binlog"):
		if current_binlog_set_to:
			frappe.db.set_value(
				"MariaDB Binlog",
				{"database_server": job.server, "file_name": json_data.get("current_binlog")},
				"current",
				0,
			)
		frappe.db.set_value(
			"MariaDB Binlog",
			{"database_server": job.server, "file_name": json_data.get("current_binlog")},
			"current",
			1,
		)


def process_remove_binlogs_from_indexer_agent_job_update(job: AgentJob):
	update_binlog_indexer_status_on_agent_job_update(job)

	if job.status != "Success":
		return

	json_data = json.loads(job.data)
	binlogs_in_disk = json_data.get("unindexed_binlogs", [])
	frappe.db.set_value(
		"MariaDB Binlog",
		{
			"database_server": job.server,
			"file_name": ("in", binlogs_in_disk),
		},
		"indexed",
		0,
	)


def auto_purge_binlogs_by_size_limit():
	databases = frappe.db.get_all(
		"Database Server",
		filters={
			"status": "Active",
			"auto_purge_binlog_based_on_size": 1,
			"is_self_hosted": 0,
			"enable_binlog_indexing": 0,
		},
		pluck="name",
	)

	for database in databases:
		if has_job_timeout_exceeded():
			return
		try:
			server: DatabaseServer = frappe.get_doc("Database Server", database)
			if not server.auto_purge_binlog_based_on_size:
				continue
			server.purge_binlogs_by_configured_size_limit()
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			frappe.db.rollback()
			return
		except Exception:
			frappe.db.rollback()


def update_database_schema_sizes():
	databases = frappe.db.get_all(
		"Database Server",
		filters={
			"status": "Active",
		},
		pluck="name",
	)

	for database in databases:
		if has_job_timeout_exceeded():
			return
		try:
			server: DatabaseServer = frappe.get_doc("Database Server", database)
			server.update_database_schema_sizes()
			frappe.db.commit()
		except rq.timeouts.JobTimeoutException:
			frappe.db.rollback()
			return
		except Exception:
			frappe.db.rollback()
