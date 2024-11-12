# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class TraceServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_password: DF.Password | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		ip: DF.Data
		ip6: DF.Data | None
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		sentry_admin_email: DF.Data | None
		sentry_admin_password: DF.Password | None
		sentry_mail_login: DF.Data | None
		sentry_mail_password: DF.Password | None
		sentry_mail_port: DF.Int
		sentry_mail_server: DF.Data | None
		sentry_oauth_client_id: DF.Data | None
		sentry_oauth_client_secret: DF.Data | None
		sentry_oauth_server_url: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

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
					"sentry_mail_server": self.sentry_mail_server,
					"sentry_mail_port": self.sentry_mail_port,
					"sentry_mail_login": self.sentry_mail_login,
					"sentry_mail_password": self.get_password("sentry_mail_password"),
					"sentry_oauth_server_url": self.sentry_oauth_server_url,
					"sentry_oauth_client_id": self.sentry_oauth_client_id,
					"sentry_oauth_client_secret": self.get_password("sentry_oauth_client_secret"),
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
	def upgrade_server(self):
		self.status = "Installing"
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_upgrade_server", queue="long", timeout=2400
		)

	def _upgrade_server(self):
		try:
			ansible = Ansible(
				playbook="trace_upgrade.yml",
				server=self,
				variables={
					"server": self.name,
					"sentry_admin_email": self.sentry_admin_email,
					"sentry_mail_server": self.sentry_mail_server,
					"sentry_mail_port": self.sentry_mail_port,
					"sentry_mail_login": self.sentry_mail_login,
					"sentry_mail_password": self.get_password("sentry_mail_password"),
					"sentry_oauth_server_url": self.sentry_oauth_server_url,
					"sentry_oauth_client_id": self.sentry_oauth_client_id,
					"sentry_oauth_client_secret": self.get_password("sentry_oauth_client_secret"),
				},
			)
			play = ansible.run()
			self.reload()
			if play.status == "Success":
				self.status = "Active"
			else:
				self.status = "Broken"
		except Exception:
			self.status = "Broken"
			log_error("Trace Server Upgrade Exception", server=self.as_dict())
		self.save()

	@frappe.whitelist()
	def show_sentry_password(self):
		return self.get_password("sentry_admin_password")
