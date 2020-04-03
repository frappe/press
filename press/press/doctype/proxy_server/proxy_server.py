# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.press.doctype.agent_job.agent_job import Agent
from frappe.utils.password import get_decrypted_password
import subprocess
import shlex
from press.utils import log_error


class ProxyServer(Document):
	def ping(self):
		agent = Agent(self.name, server_type="Proxy Server")
		return agent.ping()

	def update_agent(self):
		agent = Agent(self.name, server_type="Proxy Server")
		return agent.update()

	def _setup_server(self):
		agent_password = get_decrypted_password(self.doctype, self.name, "agent_password")
		certificate_name = frappe.db.get_value(
			"Press Settings", "Press Settings", "wildcard_tls_certificate"
		)
		domain = frappe.db.get_value("Press Settings", "Press Settings", "domain")
		certificate = frappe.get_doc("TLS Certificate", certificate_name)

		command = (
			f"ansible-playbook ../apps/press/press/playbooks/proxy.yml "
			f"-i {self.name}, -u root -vv "
			f'-e "'
			f"server={self.name} workers=1 password={agent_password} domain={domain} "
			f"certificate_privkey='{certificate.privkey}' certificate_fullchain='{certificate.fullchain}' certificate_chain='{certificate.chain}' "
			'"'
		)
		try:
			subprocess.run(shlex.split(command))
			self.status = "Active"
			self.is_server_setup = True
		except Exception:
			self.status = "Broken"
			log_error("Proxy Server Setup Exception", commmand=command)
		self.save()

	def setup_server(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_server", queue="long", timeout=1200
		)
