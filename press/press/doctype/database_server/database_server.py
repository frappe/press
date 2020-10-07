# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from press.agent import Agent
from press.runner import Ansible
from press.utils import log_error


class DatabaseServer(Document):
	def validate(self):
		if self.is_new() and not self.server_id:
			server_ids = frappe.get_all(
				"Database Server", fields=["server_id"], pluck="server_id"
			)
			if server_ids:
				self.server_id = max(server_ids or []) + 1
			else:
				self.server_id = 1

	def ping_agent(self):
		agent = Agent(self.name, server_type=self.doctype)
		return agent.ping()

	def update_agent(self):
		agent = Agent(self.name, server_type=self.doctype)
		return agent.update()

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		mariadb_root_password = self.get_password("mariadb_root_password")
		certificate_name = frappe.db.get_value(
			"Press Settings", "Press Settings", "wildcard_tls_certificate"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		try:
			ansible = Ansible(
				playbook="database.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": "2",
					"password": agent_password,
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

	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_server", queue="long", timeout=1200
		)

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

	def setup_secondary(self):
		if self.is_primary:
			return
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_secondary", queue="long", timeout=1200
		)

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

	def setup_replication(self):
		if self.is_primary:
			return
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_replication", queue="long", timeout=1200
		)

	def ping_ansible(self):
		try:
			ansible = Ansible(playbook="ping.yml", server=self)
			ansible.run()

		except Exception:
			log_error("Database Server Ping Exception", server=self.as_dict())
