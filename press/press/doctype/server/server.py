# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.agent import Agent
from press.runner import Ansible
from press.utils import log_error


class Server(Document):
	def add_upstream_to_proxy(self):
		agent = Agent(self.proxy_server, server_type="Proxy Server")
		agent.new_server(self.name)

	def ping(self):
		agent = Agent(self.name)
		return agent.ping()

	def update_agent(self):
		agent = Agent(self.name)
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
				playbook="server.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": "2",
					"password": agent_password,
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
			import traceback

			traceback.print_exc()
			log_error("Server Setup Exception")
		self.save()

	def setup_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_setup_server", queue="long", timeout=1200
		)

	def cleanup_unused_files(self):
		agent = Agent(self.name)
		agent.cleanup_unused_files()


def process_new_server_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Server", job.upstream, "is_upstream_setup", True)


def cleanup_unused_files():
	servers = frappe.get_all("Server", fields=["name"], filters={"status": "Active"})
	for server in servers:
		try:
			frappe.get_doc("Server", server.name).cleanup_unused_files()
		except Exception:
			log_error("Server File Cleanup Error", server=server)
