# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import frappe

from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class NFSServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.mount_enabled_server.mount_enabled_server import MountEnabledServer

		agent_password: DF.Password | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		ip: DF.Data
		is_server_prepared: DF.Check
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
		mount_enabled_servers: DF.Table[MountEnabledServer]
		private_ip: DF.Data
		private_mac_address: DF.Data | None
		private_vlan_id: DF.Data | None
		provider: DF.Literal["Generic", "Scaleway", "AWS EC2", "OCI"]
		root_public_key: DF.Code | None
		ssh_port: DF.Int
		ssh_user: DF.Data | None
		status: DF.Literal["Pending", "Installing", "Active", "Broken", "Archived"]
		tls_certificate_renewal_failed: DF.Check
		virtual_machine: DF.Link | None
	# end: auto-generated types

	def validate(self):
		self.validate_agent_password()
		self.validate_monitoring_password()

	def validate_monitoring_password(self):
		if not self.monitoring_password:
			self.monitoring_password = frappe.generate_hash()

	def _setup_server(self):
		agent_password = self.get_password("agent_password")
		agent_repository_url = self.get_agent_repository_url()
		monitoring_password = self.get_password("monitoring_password", False)
		certificate_name = frappe.db.get_value(
			"TLS Certificate", {"wildcard": True, "domain": self.domain}, "name"
		)
		certificate = frappe.get_doc("TLS Certificate", certificate_name)
		try:
			ansible = Ansible(
				playbook="nfs_server.yml",
				server=self,
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"server": self.name,
					"workers": 1,
					"domain": self.domain,
					"agent_password": agent_password,
					"agent_repository_url": agent_repository_url,
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
			log_error("Agent NFS Setup Exception", server=self.as_dict())

		self.save()

	@frappe.whitelist()
	def add_mount_enabled_server(
		self, server: str, use_file_system_of_server: str | None = None, share_file_system: bool = False
	) -> None:
		"""Add server to nfs servers ACL and create a shared directory"""
		if server in self.mount_enabled_servers:
			frappe.throw("Server is already mount enabled", frappe.ValidationError)

		mount_enabled_server = self.append(
			"mount_enabled_servers",
			{
				"server": server,
				"use_file_system_of_server": use_file_system_of_server,
				"share_file_system": share_file_system,
			},
		)

		mount_enabled_server.save()
		# Sharing it's directory or using someone elses directory, first preference to someone elses
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_mount_fs_on_client_and_copy_benches",
			client_server=server,
			using_fs_of_server=use_file_system_of_server or server,
			queue="long",
		)

	def _mount_fs_on_client_and_copy_benches(self, client_server: str, using_fs_of_server: str) -> None:
		try:
			ansible = Ansible(
				playbook="share_benches_on_nfs.yml",
				server=frappe.get_doc("Server", client_server),
				user=self._ssh_user(),
				port=self._ssh_port(),
				variables={
					"nfs_server_private_ip": self.private_ip,
					"using_fs_of_server": using_fs_of_server,
					"shared_directory": "/shared",
				},
			)
			ansible.run()
		except Exception:
			log_error("Client Mount Exception", server=self.as_dict())

		self.save()
