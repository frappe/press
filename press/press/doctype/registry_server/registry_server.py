# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class RegistryServer(BaseServer):
	def validate(self):
		self.validate_agent_password()
		self.validate_registry_username()
		self.validate_registry_password()

	def validate_registry_password(self):
		if not self.registry_password:
			self.registry_password = frappe.generate_hash(length=32)

	def validate_registry_username(self):
		if not self.registry_username:
			self.registry_username = "frappe"

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		try:
			ansible = Ansible(
				playbook="registry.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"agent_password": agent_password,
					"private_ip": self.private_ip,
					"registry_username": self.registry_username,
					"registry_password": self.get_password("registry_password"),
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
			log_error("Registry Server Setup Exception", server=self.as_dict())
		self.save()
