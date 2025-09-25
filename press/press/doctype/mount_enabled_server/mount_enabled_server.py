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
		server: DF.Link
		share_file_system: DF.Check
		use_file_system_of_server: DF.Link | None
		using_volume: DF.Link | None
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
		)

	def _attach_volume_on_nfs_server(self, volume_size: int) -> str:
		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.parent)
		return virtual_machine.attach_new_volume(volume_size, iops=3000, throughput=124)

	def attach_volume_and_move_data(
		self, client_server: str, using_fs_of_server: str, share_file_system: bool
	) -> None:
		"""
		Attach an EBS volume to the NFS server for the client sharing their file system,
		or update the volume name on servers using a shared volume.
		"""

		def _update_volume_mapping(server: str, volume_name: str) -> None:
			"""Update the `using_volume` field for a given server."""
			frappe.db.set_value(
				"Mount Enabled Server",
				{"server": server, "parent": self.name},
				"using_volume",
				volume_name,
			)
			frappe.db.commit()

		if not share_file_system:
			# Get existing volume from the server that is already sharing its fs
			# If using someone elses fs then we don't need to move our data to it
			volume_name = frappe.db.get_value(
				"Mount Enabled Server",
				{"parent": self.name, "server": using_fs_of_server},
				"using_volume",
			)
			_update_volume_mapping(client_server, volume_name)
		else:
			# Create & attach a new volume for the NFS server
			volume_size = frappe.db.get_value("Virtual Machine", using_fs_of_server, "disk_size")
			volume_id = self._attach_volume_on_nfs_server(volume_size=volume_size)
			volume_name = frappe.db.get_value(
				"Virtual Machine Volume",
				{"parent": self.name, "volume_id": volume_id},
				"name",
			)

			_update_volume_mapping(client_server, volume_name)
			self._mount_fs_on_client_and_copy_benches(client_server, using_fs_of_server)

	def _mount_fs_on_client_and_copy_benches(self, client_server: str, using_fs_of_server: str) -> None:
		try:
			ansible = Ansible(
				playbook="share_benches_on_nfs.yml",
				server=frappe.get_cached_doc("Server", client_server),
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

	def on_delete(self): ...
