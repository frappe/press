# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
import os
import base64

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class AnalyticsServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_password: DF.Password | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		google_client_id: DF.Data | None
		google_client_secret: DF.Password | None
		hostname: DF.Data
		ip: DF.Data
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		plausible_mail_login: DF.Data | None
		plausible_mail_password: DF.Password | None
		plausible_mail_port: DF.Int
		plausible_mail_server: DF.Data | None
		plausible_password: DF.Password | None
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_agent_password()
		self.validate_monitoring_password()
		self.validate_plausible_password()

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def validate_plausible_password(self):
		if not self.plausible_password:
			self.plausible_password = frappe.generate_hash()

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
				playbook="analytics.yml",
				server=self,
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"log_server": log_server,
					"agent_password": self.get_password("agent_password"),
					"agent_repository_url": agent_repository_url,
					"kibana_password": kibana_password,
					"plausible_password": self.get_password("plausible_password"),
					"plausible_secret": base64.b64encode(os.urandom(64)).decode(),
					"plausible_mail_server": self.plausible_mail_server,
					"plausible_mail_port": self.plausible_mail_port,
					"plausible_mail_login": self.plausible_mail_login,
					"plausible_mail_password": self.get_password("plausible_mail_password"),
					"google_client_id": self.google_client_id,
					"google_client_secret": self.get_password("google_client_secret"),
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
			log_error("Analytics Server Setup Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def show_plausible_password(self):
		return self.get_password("plausible_password")
