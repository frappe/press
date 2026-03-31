# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import frappe

from press.press.doctype.nfs_volume_attachment.nfs_volume_attachment import NFSVolumeAttachment
from press.press.doctype.nfs_volume_detachment.nfs_volume_detachment import NFSVolumeDetachment
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error


class NFSServer(BaseServer):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agent_password: DF.Password | None
		cluster: DF.Link | None
		domain: DF.Link | None
		frappe_public_key: DF.Code | None
		frappe_user_password: DF.Password | None
		hostname: DF.Data
		ip: DF.Data
		is_server_prepared: DF.Check
		is_server_setup: DF.Check
		monitoring_password: DF.Password | None
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
		# self.validate_monitoring_password()

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
		self,
		server: str,
	) -> NFSVolumeAttachment:
		"""Add server to nfs servers ACL and create a shared directory"""
		secondary_server = frappe.get_value("Server", server, "secondary_server")
		nfs_volume_attachment: NFSVolumeAttachment = frappe.get_doc(
			{
				"doctype": "NFS Volume Attachment",
				"nfs_server": self.name,
				"primary_server": server,
				"secondary_server": secondary_server,
			}
		)
		return nfs_volume_attachment.insert()

	@frappe.whitelist()
	def remove_mount_enabled_server(self, server: str) -> NFSVolumeDetachment:
		secondary_server = frappe.get_value("Server", server, "secondary_server")
		nfs_volume_detachment: NFSVolumeDetachment = frappe.get_doc(
			{
				"doctype": "NFS Volume Detachment",
				"nfs_server": self.name,
				"primary_server": server,
				"secondary_server": secondary_server,
			}
		)
		return nfs_volume_detachment.insert()
