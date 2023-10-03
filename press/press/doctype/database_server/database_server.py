# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from typing import Any
import frappe
from frappe.core.doctype.version.version import get_diff

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
	DatabaseServerMariaDBVariable,
)
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error
from frappe.core.utils import find


class DatabaseServer(BaseServer):
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
		if self.has_value_changed("memory_high") or self.has_value_changed("memory_max"):
			self.update_memory_limits()

		if (
			self.has_value_changed("team")
			and self.subscription
			and self.subscription.team != self.team
		):

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

	def update_memory_limits(self):
		frappe.enqueue_doc(self.doctype, self.name, "_update_memory_limits")

	def _update_memory_limits(self):
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
			},
		)
		play = ansible.run()
		if play.status == "Failure":
			log_error("Database Server Update Memory Limits Error", server=self.name)

	def update_mariadb_system_variables(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_update_mariadb_system_variables",
			queue="long",
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
		return self.get_changed_variables(
			diff.get("row_changed", {})
		) + self.get_newly_added_variables(diff.get("added", []))

	def _update_mariadb_system_variables(
		self, variables: list[DatabaseServerMariaDBVariable] = []
	):
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

	def add_mariadb_variable(
		self,
		variable: str,
		value_type: str,
		value: Any,
		skip: bool = False,
		persist: bool = True,
	):
		"""Add or update MariaDB variable on the server"""
		existing = find(
			self.mariadb_system_variables, lambda x: x.mariadb_variable == variable
		)
		if existing:
			existing.set(value_type, value)
			existing.set("skip", skip)
			existing.set("persist", persist)
		else:
			self.append(
				"mariadb_system_variables",
				{
					"mariadb_variable": variable,
					value_type: value,
					"skip": skip,
					"persist": persist,
				},
			)
		self.save()

	def validate_server_id(self):
		if self.is_new() and not self.server_id:
			server_ids = frappe.get_all(
				"Database Server", fields=["server_id"], pluck="server_id"
			)
			if server_ids:
				self.server_id = max(server_ids or []) + 1
			else:
				self.server_id = 1

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		mariadb_root_password = self.get_password("mariadb_root_password")
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
				playbook="self_hosted_db.yml"
				if getattr(self, "is_self_hosted", False)
				else "database.yml",
				server=self,
				user=self.ssh_user or "root",
				port=self.ssh_port or 22,
				variables={
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
				self.is_server_setup = True
				if self.is_self_hosted:
					server = frappe.get_doc("Server", self.name)
					if server.status != "Active":
						server.setup_server()  # Setup App server after DB server setup
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Database Server Setup Exception", server=self.as_dict())
		self.save()

	def _setup_primary(self, secondary):
		mariadb_root_password = self.get_password("mariadb_root_password")
		secondary_root_public_key = frappe.db.get_value(
			"Database Server", secondary, "root_public_key"
		)
		try:
			ansible = Ansible(
				playbook="primary.yml",
				server=self,
				variables={
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
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_replication", queue="long", timeout=18000
		)

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
		frappe.enqueue_doc(
			self.doctype, self.name, "_trigger_failover", queue="long", timeout=1200
		)

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
		frappe.enqueue_doc(
			self.doctype, self.name, "_convert_from_frappe_server", queue="long", timeout=1200
		)

	def _install_exporters(self):
		mariadb_root_password = self.get_password("mariadb_root_password")
		monitoring_password = frappe.get_doc("Cluster", self.cluster).get_password(
			"monitoring_password"
		)
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

	@frappe.whitelist()
	def enable_performance_schema(self):
		for key, value in PERFORMANCE_SCHEMA_VARIABLES.items():
			if isinstance(value, int):
				type_key = "value_int"
			elif isinstance(value, str):
				type_key = "value_str"

			existing_variable = find(
				self.mariadb_system_variables, lambda x: x.mariadb_variable == key
			)

			if existing_variable:
				existing_variable.set(type_key, value)
			else:
				self.append(
					"mariadb_system_variables",
					{"mariadb_variable": key, type_key: value, "persist": True},
				)

		self.is_performance_schema_enabled = True
		self.save()

	@frappe.whitelist()
	def disable_performance_schema(self):
		existing_variable = find(
			self.mariadb_system_variables, lambda x: x.mariadb_variable == "performance_schema"
		)
		if existing_variable:
			existing_variable.value_str = "OFF"
		else:
			self.append(
				"mariadb_system_variables",
				{"mariadb_variable": "performance_schema", "value_str": "OFF", "persist": True},
			)

		self.is_performance_schema_enabled = False
		self.save()

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
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_deadlock_logger", queue="long", timeout=1200
		)

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

	def _rename_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		mariadb_root_password = self.get_password("mariadb_root_password")
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
				playbook="database_rename.yml",
				server=self,
				variables={
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

	def adjust_memory_config(self):
		if not self.ram:
			return

		self.memory_high = max(self.ram // 1024 - 2, 1)
		self.memory_max = max(self.ram // 1024 - 1, 2)
		self.save()

		self.add_mariadb_variable(
			"innodb_buffer_pool_size",
			"value_int",
			int(self.ram * 0.685),  # will be rounded up based on chunk_size
		)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Database Server"
)

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
