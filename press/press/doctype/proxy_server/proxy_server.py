# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.agent import Agent
from press.utils import log_error
from frappe.utils import unique


class ProxyServer(BaseServer):
	def validate(self):
		super().validate()
		self.validate_domains()

	def validate_domains(self):
		domains = [row.domain for row in self.domains]
		# Always include self.domain in the domains child table
		# Remove duplicates
		domains = unique([self.domain] + domains)
		self.domains = []
		for domain in domains:
			if not frappe.db.exists(
				"TLS Certificate", {"wildcard": True, "status": "Active", "domain": domain}
			):
				frappe.throw(f"Valid wildcard TLS Certificate not found for {domain}")
			self.append("domains", {"domain": domain})

	def get_wildcard_domains(self):
		wildcard_domains = []
		for domain in self.domains:
			if domain.domain == self.domain:
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
				}
			)
		return wildcard_domains

	def setup_wildcard_hosts(self):
		agent = Agent(self.name, server_type="Proxy Server")
		wildcards = self.get_wildcard_domains()
		agent.setup_wildcard_hosts(wildcards)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		domain = frappe.db.get_value("Press Settings", "Press Settings", "domain")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
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
					"agent_password": agent_password,
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
