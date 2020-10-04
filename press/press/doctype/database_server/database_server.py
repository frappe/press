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
					"mariadb_root_password": mariadb_root_password,
					"certificate_private_key": certificate.private_key,
					"certificate_full_chain": certificate.full_chain,
					"certificate_intermediate_chain": certificate.intermediate_chain,
				},
			)
			play = ansible.run()
			if play.status == "Success":
				self.status = "Active"
				self.is_server_setup = True
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Database Server Setup Exception")
		self.save()

	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_server", queue="long", timeout=1200
		)

