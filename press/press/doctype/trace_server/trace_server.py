# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class TraceServer(BaseServer):
	def validate(self):
		self.validate_agent_password()
		self.validate_monitoring_password()
		self.validate_sentry_admin_password()

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def validate_sentry_admin_password(self):
		if not self.sentry_admin_password:
			self.sentry_admin_password = frappe.generate_hash()

	def _setup_server(self):
		agent_repository_url = self.get_agent_repository_url()
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)

		log_server = frappe.db.get_single_value("Press Settings", "log_server")
		if log_server:
			kibana_password = frappe.get_doc("Log Server", log_server).get_password(
				"kibana_password"
			)
		else:
			kibana_password = None

		try:
			ansible = Ansible(
				playbook="trace.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"log_server": log_server,
					"agent_password": self.get_password("agent_password"),
					"agent_repository_url": agent_repository_url,
					"kibana_password": kibana_password,
					"sentry_admin_email": self.sentry_admin_email,
					"sentry_admin_password": self.get_password("sentry_admin_password"),
					"monitoring_password": self.get_password("monitoring_password"),
					"private_ip": self.private_ip,
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
			log_error("Trace Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def show_sentry_password(self):
		return self.get_password("sentry_admin_password")
