# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from typing import Any, Literal

import frappe
import frappe.utils
from frappe.core.doctype.version.version import get_diff
from frappe.core.utils import find

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
	DatabaseServerMariaDBVariable,
)
from press.press.doctype.server.server import Agent, BaseServer
from press.runner import Ansible
from press.utils import log_error


class DatabaseServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
			DatabaseServerMariaDBVariable,
		)
		from press.press.doctype.resource_tag.resource_tag import ResourceTag
		from press.press.doctype.server_mount.server_mount import ServerMount

		agent_password: DF.Password | None
		auto_add_storage_max: DF.Int
		auto_add_storage_min: DF.Int
		cluster: DF.Link | None
		domain: DF.Link | None
		enable_physical_backup: DF.Check
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		has_data_volume: DF.Check
		hostname: DF.Data
		hostname_abbreviation: DF.Data | None
		ip: DF.Data | None
		is_performance_schema_enabled: DF.Check
		is_primary: DF.Check
		is_replication_setup: DF.Check
		is_self_hosted: DF.Check
		is_server_prepared: DF.Check
		is_server_renamed: DF.Check
		is_server_setup: DF.Check
		is_stalk_setup: DF.Check
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
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
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

	def validate(self):
		super().validate()
		self.validate_mariadb_root_password()
		self.validate_server_id()
		self.validate_mariadb_system_variables()

	def validate_mariadb_root_password(self):
		if not self.mariadb_root_password:
			self.mariadb_root_password = frappe.generate_hash(length=32)

	def validate_mariadb_system_variables(self):
		variable: DatabaseServerMariaDBVariable
		for variable in self.mariadb_system_variables:
			variable.validate()

	def on_update(self):
		if self.flags.in_insert or self.is_new():
			return
		self.update_mariadb_system_variables()
		if (
			self.has_value_changed("memory_high")
			or self.has_value_changed("memory_max")
			or self.has_value_changed("memory_swap_max")
		):
			self.update_memory_limits()

		if self.has_value_changed("team") and self.subscription and self.subscription.team != self.team:
			self.subscription.disable()

			# enable subscription if exists
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
					frappe.log_error("Database Subscription Creation Error")

	def get_doc(self, doc):
		doc = super().get_doc(doc)
		doc.mariadb_variables = {
			"innodb_buffer_pool_size": self.get_mariadb_variable_value(
				"innodb_buffer_pool_size", return_default_if_not_found=True
			),
			"max_connections": frappe.utils.cint(
				self.get_mariadb_variable_value("max_connections", return_default_if_not_found=True)
			),
		}
		doc.mariadb_variables_recommended_values = {
			"innodb_buffer_pool_size": self.recommended_innodb_buffer_pool_size,
			"max_connections": self.recommended_max_db_connections,
		}
		return doc

	def get_actions(self):
		server_actions = super().get_actions()
		server_type = "database server"
		actions = [
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
			{
				"action": "View Database Configuration",
				"description": "View Database Configuration",
				"button_label": "View",
				"condition": self.status == "Active",
				"doc_method": "get_mariadb_variables",
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
		value: Any = None,
		skip: bool = False,
		persist: bool = True,
		save: bool = True,
		avoid_update_if_exists: bool = False,
	):
		"""Add or update MariaDB variable on the server"""
		if not skip and not value:
			frappe.throw("For non-skippable variables, value is mandatory")

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
			self.save()

	@dashboard_whitelist()
	def get_mariadb_variable_value(
		self, variable: str, return_default_if_not_found: bool = False
	) -> str | int | float | None:
		existing = find(self.mariadb_system_variables, lambda x: x.mariadb_variable == variable)
		if not existing:
			return None

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
					"monitoring_password": config.monitoring_password,
					"log_server": config.log_server,
					"kibana_password": config.kibana_password,
					"private_ip": self.private_ip,
					"server_id": self.server_id,
					"allocator": self.memory_allocator.lower(),
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
				mariadb_root_password=self.get_password("mariadb_root_password"),
				certificate=certificate,
				monitoring_password=frappe.get_doc("Cluster", self.cluster).get_password(
					"monitoring_password"
				),
				log_server=log_server,
				kibana_password=kibana_password,
			)
		)

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
				variables={
					"backup_path": "/tmp/replica",
					"mariadb_root_password": mariadb_root_password,
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
				variables={
					"mariadb_root_password": mariadb_root_password,
					"primary_private_ip": primary.private_ip,
					"private_ip": self.private_ip,
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
				servers = frappe.get_all("Server", {"database_server": old_primary})
				for server in servers:
					server = frappe.get_doc("Server", server.name)
					server.database_server = self.name
					server.save()
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Database Server Failover Exception", server=self.as_dict())
		self.save()

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
				variables={
					"mariadb_old_root_password": old_password,
					"mariadb_root_password": self.mariadb_root_password,
					"private_ip": self.private_ip,
				},
			)
			ansible.run()
			self.save()
		except Exception:
			log_error("Database Server Password Reset Exception", server=self.as_dict())
			raise

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
				variables={
					"mariadb_root_password": self.mariadb_root_password,
					"private_ip": self.private_ip,
				},
			)
			ansible.run()
			self.save()
		except Exception:
			log_error("Database Server Password Reset Exception", server=self.as_dict())
			raise

	@frappe.whitelist()
	def setup_deadlock_logger(self):
		frappe.enqueue_doc(self.doctype, self.name, "_setup_deadlock_logger", queue="long", timeout=1200)

	def _setup_deadlock_logger(self):
		try:
			ansible = Ansible(
				playbook="deadlock_logger.yml",
				server=self,
				variables={
					"server": self.name,
					"mariadb_root_password": self.get_password("mariadb_root_password"),
				},
			)
			ansible.run()
		except Exception:
			log_error("Deadlock Logger Setup Exception", server=self.as_dict())

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
	def adjust_memory_config(self):
		if not self.ram:
			return

		self.memory_high = round(max(self.ram_for_mariadb / 1024 - 1, 1), 3)
		self.memory_max = round(max(self.ram_for_mariadb / 1024, 2), 3)

		max_recommended_connections = self.recommended_max_db_connections
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
		self.save()

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
