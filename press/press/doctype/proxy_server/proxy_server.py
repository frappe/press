# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.press.doctype.agent_job.agent_job import Agent
from press.runner import Ansible
from press.utils import log_error


class ProxyServer(Document):
	def validate(self):
		if self.is_new() and not self.cluster:
			self.cluster = frappe.db.get_value("Cluster", {"default": True})

	def ping_agent(self):
		agent = Agent(self.name, server_type="Proxy Server")
		return agent.ping()

	def update_agent(self):
		agent = Agent(self.name, server_type="Proxy Server")
		return agent.update()

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		domain = frappe.db.get_value("Press Settings", "Press Settings", "domain")
		certificate_name = frappe.db.get_value(
			"Press Settings", "Press Settings", "wildcard_tls_certificate"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		try:
			ansible = Ansible(
				playbook="proxy.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": domain,
					"password": agent_password,
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
			log_error("Proxy Server Setup Exception", server=self.as_dict())
		self.save()

	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_server", queue="long", timeout=1200
		)

	def ping_ansible(self):
		try:
			ansible = Ansible(playbook="ping.yml", server=self)
			ansible.run()
		except Exception:
			log_error("Proxy Server Ping Exception", server=self.as_dict())
