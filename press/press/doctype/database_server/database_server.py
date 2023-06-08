# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.core.doctype.version.version import get_diff

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.database_server_mariadb_variable.database_server_mariadb_variable import (
	DatabaseServerMariaDBVariable,
)
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


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
		self.update_mariadb_system_variables()
		if self.has_value_changed("memory_high") or self.has_value_changed("memory_max"):
			self.update_memory_limits()

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
		diff = get_diff(old_doc, self)
		return self.get_newly_added_variables(
			diff.get("added", [])
		) + self.get_changed_variables(diff.get("row_changed", {}))

	def _update_mariadb_system_variables(
		self, variables: list[DatabaseServerMariaDBVariable] = []
	):
		for variable in variables:
			variable.update_on_server()

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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Database Server"
)
