# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class LogServer(BaseServer):
	def validate(self):
		self.validate_agent_password()
		self.validate_monitoring_password()
		self.validate_kibana_password()

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def validate_kibana_password(self):
		if not self.kibana_password:
			self.kibana_password = frappe.generate_hash()

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		kibana_password = self.get_password("kibana_password")
		monitoring_password = self.get_password("monitoring_password")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		try:
			ansible = Ansible(
				playbook="log.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"log_server": self.name,
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
					"kibana_password": kibana_password,
					"monitoring_password": monitoring_password,
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
			log_error("Log Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def show_kibana_password(self):
		return self.get_password("kibana_password")

	@frappe.whitelist()
	def install_elasticsearch_exporter(self):
		frappe.enqueue_doc(
			self.doctype, self.name, "_install_elasticsearch_exporter", queue="long", timeout=1200
		)

	def _install_elasticsearch_exporter(self):
		try:
			ansible = Ansible(
				playbook="elasticsearch_exporter.yml",
				server=self
			)
			ansible.run()
		except Exception:
			log_error("Elasticsearch Exporter Install Exception", server=self.as_dict())
