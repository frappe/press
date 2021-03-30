# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class MonitoringServer(BaseServer):
	def validate(self):
		self.validate_agent_password()
		self.validate_prometheus_username()
		self.validate_prometheus_password()
		self.validate_grafana_password()

	def validate_prometheus_password(self):
		if not self.prometheus_password:
			self.prometheus_password = frappe.generate_hash(length=32)

	def validate_prometheus_username(self):
		if not self.prometheus_username:
			self.prometheus_username = "frappe"

	def validate_grafana_password(self):
		if not self.grafana_password:
			self.grafana_password = frappe.generate_hash(length=32)

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		try:
			ansible = Ansible(
				playbook="monitoring.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"agent_password": agent_password,
					"private_ip": self.private_ip,
					"prometheus_username": self.prometheus_username,
					"prometheus_password": self.get_password("prometheus_password"),
					"grafana_password": self.get_password("grafana_password"),
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
			log_error("Monitoring Server Setup Exception", server=self.as_dict())
		self.save()
