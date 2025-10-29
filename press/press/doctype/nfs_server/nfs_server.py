# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt


import typing

import frappe

from press.agent import Agent
from press.press.doctype.nfs_volume_attachment.nfs_volume_attachment import NFSVolumeAttachment
from press.press.doctype.nfs_volume_detachment.nfs_volume_detachment import NFSVolumeDetachment
from press.press.doctype.server.server import BaseServer
from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob


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


class SwitchServers:
	def __init__(self, primary_server: str, secondary_server: str) -> None:
		self.primary_server = primary_server
		self.secondary_server = secondary_server
		self.primary_server_private_ip = frappe.db.get_value("Server", self.primary_server, "private_ip")
		self.secondary_server_private_ip = frappe.db.get_value("Server", self.secondary_server, "private_ip")

	@property
	def have_workers_stopped_on_primary_server(self) -> bool:
		status = frappe.get_value(
			"Agent Job", {"server": self.primary_server, "job_type": "Stop Bench Workers"}, "status"
		)
		return status == "Success"

	def run_primary_server_benches_on_shared_fs(self) -> "AgentJob":
		"""
		Runs the following steps:
			1. Changes benches_directory to `/shared`
			2. Updates agent nginx config file to include `/shared/*/nginx.conf`
			3. Updates benches nginx config file update the root dir
			4. Restarts benches
		"""
		return Agent(self.primary_server).run_benches_on_shared_fs(
			redis_connection_string_ip=None,
			secondary_server_private_ip=self.secondary_server_private_ip,
			is_primary=True,
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

	def stop_workers_on_primary_server(self) -> "AgentJob":
		return Agent(self.primary_server).stop_bench_workers("Server", self.primary_server)

	def start_workers_on_primary_server(self) -> "AgentJob":
		return Agent(self.primary_server).start_bench_workers("Server", self.primary_server)

	def switch_to_primary(self) -> "AgentJob":
		"""
		Updates common site config with redis connection string and
		bench directories in all the configs.
		"""
		return Agent(self.primary_server).run_benches_on_shared_fs(
			redis_connection_string_ip="localhost",
			secondary_server_private_ip=self.secondary_server_private_ip,
			is_primary=True,
			restart_benches=False,
			reference_doctype="Server",
			reference_name=self.primary_server,
		)

	def switch_to_secondary(self):
		"""
		Updates common site config with redis connection string and
		bench directories in all the configs.
		"""
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["docker_registry_url", "docker_registry_username", "docker_registry_password"],
			as_dict=True,
		)

		if not self.have_workers_stopped_on_primary_server:
			raise RuntimeError("Benches on primary server are still running all workers")

		return Agent(self.secondary_server).run_benches_on_shared_fs(
			redis_connection_string_ip=self.primary_server_private_ip,
			secondary_server_private_ip=self.secondary_server_private_ip,
			is_primary=False,
			registry_settings={
				"url": settings.docker_registry_url,
				"username": settings.docker_registry_username,
				"password": settings.docker_registry_password,
			},
			restart_benches=True,
			reference_doctype="Server",
			reference_name=self.secondary_server,
		)

	def force_remove_all_benches(self) -> "AgentJob":
		return Agent(self.secondary_server).force_remove_all_benches("Server", self.secondary_server)
