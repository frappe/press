# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class ProxyServer(BaseServer):
	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		domain = frappe.db.get_value("Press Settings", "Press Settings", "domain")
		certificate_name = frappe.db.get_value("TLS Certificate", {"wildcard": True, "domain": self.domain}, "name")
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
