# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

from press.agent import HTTPError
from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.nfs_server.nfs_server import NFSServer
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class MountEnabledServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		ready_to_share_file_system: DF.Check
		server: DF.Link
		share_file_system: DF.Check
		use_file_system_of_server: DF.Link | None
		using_volume: DF.Data | None
	# end: auto-generated types

	def add_server_to_nfs_acl(self):
		nfs_server: NFSServer = frappe.get_doc("NFS Server", self.parent)
		private_ip = frappe.db.get_value("Server", self.server, "private_ip")
		nfs_server.agent.post(
			"/nfs/exports",
			data={
				"server": self.server,
				"private_ip": private_ip,
				"share_file_system": self.share_file_system,
				"use_file_system_of_server": self.use_file_system_of_server,
			},
		)

	def before_insert(self):
		if self.share_file_system:
			return

		is_ready = frappe.db.get_value(
			"Mount Enabled Server",
			{"parent": self.parent, "server": self.use_file_system_of_server},
			"ready_to_share_file_system",
		)

		if not is_ready:
			frappe.throw(
				f"Server {self.use_file_system_of_server} is not ready to share the file system, wait for sometime"
			)

	def after_insert(self):
		try:
			self.add_server_to_nfs_acl()
		except HTTPError:
			frappe.throw("Unable to add server to ACL")

		# Sharing it's directory or using someone elses directory, first preference to someone elses
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"attach_volume_and_move_data",
			client_server=self.server,
			using_fs_of_server=self.use_file_system_of_server or self.server,
			share_file_system=self.share_file_system,
			queue="long",
			timeout=18000,
		)

	def _attach_volume_on_nfs_server(self, volume_size: int) -> str:
		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.parent)
		return virtual_machine.attach_new_volume(volume_size, iops=3000, throughput=124, log_activity=False)

	def _format_and_mount_fs(self, volume_id: str) -> None:
		"""Create a filesystem from newly mounted volume and mount shared directory on it"""
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.parent)
		ansible = Ansible(
			playbook="mount_ebs_on_nfs_server.yml",
			server=nfs_server,  # Mounting on NFS Server
			user=nfs_server._ssh_user(),
			port=nfs_server._ssh_port(),
			variables={
				"shared_directory": f"/home/frappe/nfs/{self.use_file_system_of_server or self.server}",
				"volume_id": volume_id.replace("vol-", ""),
			},
		)
		ansible.run()

	def _mount_shared_folder(self, client_server: str, using_fs_of_server: str) -> None:
		client_server: Server = frappe.get_cached_doc("Server", client_server)
		nfs_server_private_ip = frappe.db.get_value("NFS Server", self.parent, "private_ip")
		try:
			ansible = Ansible(
				playbook="mount_shared_folder.yml",
				server=client_server,
				user=client_server._ssh_user(),
				port=client_server._ssh_port(),
				variables={
					"nfs_server_private_ip": nfs_server_private_ip,
					"using_fs_of_server": using_fs_of_server,
					"shared_directory": "/shared",
				},
			)
			ansible.run()
		except Exception:
			log_error("Exception While Mounting Shared FS", server=self.as_dict())

	def _move_benches_to_shared(self, client_server: str) -> None:
		client_server: Server = frappe.get_cached_doc("Server", client_server)
		try:
			ansible = Ansible(
				playbook="share_benches_on_nfs.yml",
				server=client_server,
				user=client_server._ssh_user(),
				port=client_server._ssh_port(),
			)
			ansible.run()
		except Exception:
			log_error("Exception While Moving Benches to Shared FS", server=self.as_dict())

	def mount_shared_folder(
		self, client_server: str, using_fs_of_server: str, move_benches: bool = False
	) -> None:
		self._mount_shared_folder(client_server, using_fs_of_server)

		if move_benches:
			self._move_benches_to_shared(client_server)

	def attach_volume_and_move_data(
		self, client_server: str, using_fs_of_server: str, share_file_system: bool
	) -> None:
		"""
		Attach an EBS volume to the NFS server for the client sharing their file system,
		or update the volume name on servers using a shared volume.
		"""
		if not share_file_system:
			# Get existing volume from the server that is already sharing its fs
			# If using someone elses fs then we don't need to move our data to it
			volume_name = frappe.db.get_value(
				"Mount Enabled Server",
				{"parent": self.parent, "server": using_fs_of_server},
				"using_volume",
			)

			self.using_volume = volume_name
			self.save()

			self.mount_shared_folder(
				client_server=client_server, using_fs_of_server=using_fs_of_server, move_benches=False
			)
		else:
			# Create & attach a new volume for the NFS server
			volume_size = frappe.db.get_value("Virtual Machine", using_fs_of_server, "disk_size")
			volume_id = self._attach_volume_on_nfs_server(volume_size=volume_size)
			self._format_and_mount_fs(volume_id)

			self.using_volume = volume_id
			self.save()

			self.mount_shared_folder(
				client_server=client_server, using_fs_of_server=using_fs_of_server, move_benches=True
			)

			self.ready_to_share_file_system = True
			self.save()

	def on_delete(self): ...
