# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
import requests

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class DeadmanServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		admin_password: DF.Password | None
		deadman_password: DF.Password | None
		deadman_repo: DF.Data | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		ip: DF.Data | None
		is_server_setup: DF.Check
		mariadb_root_password: DF.Password | None
		plan: DF.Link | None
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		root_public_key: DF.Code | None
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tls_certificate_renewal_failed: DF.Check
	# end: auto-generated types

	def validate(self):
		self.validate_admin_password()
		self.validate_deadman_password()
		self.validate_mariadb_root_password()

	def validate_admin_password(self):
		if not self.admin_password:
			self.admin_password = frappe.generate_hash(length=32)

	def validate_deadman_password(self):
		if not self.deadman_password:
			self.deadman_password = frappe.generate_hash(length=32)

	def validate_mariadb_root_password(self):
		if not self.mariadb_root_password:
			self.mariadb_root_password = frappe.generate_hash(length=32)

	def _setup_server(self):
		self.reload()

		admin_password = self.get_password("admin_password")
		deadman_password = self.get_password("deadman_password")
		mariadb_root_password = self.get_password("mariadb_root_password")

		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)

		try:
			ansible = Ansible(
				playbook="deadman.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"domain": self.domain,
					"deadman_repo": self.deadman_repo,
					"admin_password": admin_password,
					"deadman_password": deadman_password,
					"mariadb_root_password": mariadb_root_password,
					"private_ip": self.private_ip,
					"server_id": 1,
					"db_port": 3306,
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

			log_error(
				"Deadman Server Setup Exception",
				server=self.as_dict(),
			)

		self.save()

	def send_capability_heartbeat(self, capability_name):
		url = f"https://{self.hostname}.{self.domain}/api/method/deadman.deadman.api.capability.update_capability_heartbeat"
		print(url)

		response = requests.post(
			url,
			data={
				"capability_name": capability_name,
				"password": self.get_password("deadman_password"),
			},
			timeout=15,
		)

		response.raise_for_status()
