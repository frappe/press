# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document
from requests.exceptions import HTTPError

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

		move_benches: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		ready_to_share_file_system: DF.Check
		server: DF.Link
		share_file_system: DF.Check
		use_file_system_of_server: DF.Link | None
		using_volume: DF.Data | None
		volume_size: DF.Int
	# end: auto-generated types

	@property
	def is_file_system_being_shared(self) -> bool:
		"""Check if any other server is currently using the filesystem"""
		return bool(
			frappe.db.get_value(
				"Mount Enabled Server",
				{
					"parent": self.parent,
					"use_file_system_of_server": self.server,
				},
			)
		)

	def add_server_to_nfs_acl(self):
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.parent)
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

	def remove_server_from_nfs_acl(self):
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.parent)

		if self.share_file_system and self.is_file_system_being_shared:
			frappe.throw("File system is being used by another server please unmount that first!")

		private_ip = frappe.db.get_value("Server", self.server, "private_ip")
		nfs_server.agent.delete(
			"/nfs/exports",
			data={
				"private_ip": private_ip,
				"file_system": self.use_file_system_of_server if not self.share_file_system else self.server,
			},
		)

	def validate(self):
		if not self.share_file_system and self.move_benches:
			frappe.throw("Can not move benches if server is not sharing the file system")

		if not self.share_file_system and self.volume_size:
			frappe.throw("No new volume being created since server is not sharing it's the file system")

	def on_trash(self):
		try:
			self.remove_server_from_nfs_acl()
		except HTTPError:
			frappe.throw("Unable to remove server from ACL")

		if self.share_file_system:
			frappe.enqueue(
				"press.press.doctype.mount_enabled_server.mount_enabled_server.detach_umount_and_delete_volume_on_nfs",
				nfs_server=self.parent,
				volume_id=self.using_volume,
				shared_directory=self.server,
				queue="long",
			)

		frappe.enqueue(
			"press.press.doctype.mount_enabled_server.mount_enabled_server.umount_and_delete_shared_directory_on_client",
			client_server=self.server,
			nfs_server=self.parent,
			shared_directory=self.use_file_system_of_server,
			queue="long",
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
		"""Attach volume on NFS Server"""
		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.parent)
		return virtual_machine.attach_new_volume(volume_size, iops=3000, throughput=124, log_activity=False)

	def _format_and_mount_fs(self, volume_id: str) -> None:
		"""Create a filesystem from newly mounted volume and mount shared directory on it"""
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.parent)
		try:
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
		except Exception:
			log_error("Exception While Mounting Volume on NFS Server", server=self.as_dict())

	def _mount_shared_folder_on_client_server(self, client_server: str, using_fs_of_server: str) -> None:
		"""Mount shared folder on client server utilizing the shared filesystem"""
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
		"""Start to move the benches on the shared directory"""
		client_server: Server = frappe.get_cached_doc("Server", client_server)
		try:
			ansible = Ansible(
				playbook="share_benches_on_nfs.yml",
				server=client_server,
				user=client_server._ssh_user(),
				port=client_server._ssh_port(),
				variables={"nfs_server": self.parent, "client_server": client_server.name},
			)
			ansible.run()
		except Exception:
			log_error("Exception While Moving Benches to Shared FS", server=self.as_dict())

	def _get_volume_from_sharing_server(self, using_fs_of_server: str) -> str | None:
		"""Return the volume id used by another 'sharing' server."""
		return frappe.db.get_value(
			"Mount Enabled Server", {"parent": self.parent, "server": using_fs_of_server}, "using_volume"
		)

	def _create_and_attach_volume_on_nfs_server(self, using_fs_of_server: str) -> str:
		"""Create/attach a new EBS volume and format/mount filesystem on the nfs server."""
		volume_size = self.volume_size or frappe.db.get_value(
			"Virtual Machine", using_fs_of_server, "disk_size"
		)
		volume_id = self._attach_volume_on_nfs_server(volume_size=volume_size)
		self._format_and_mount_fs(volume_id)
		return volume_id

	def _allow_ssh_access_to_nfs_server(self, client_server: str):
		client_server: Server = frappe.get_cached_doc("Server", client_server)
		try:
			ansible = Ansible(
				playbook="ssh_access_to_rsync.yml",
				server=client_server,
				user=client_server._ssh_user(),
				port=client_server._ssh_port(),
				variables={
					"ssh_user": client_server._ssh_user(),
					"ssh_key_path": "/root/.ssh/id_ed25519",
					"destination_host": self.parent,  # This is the nfs server
				},
			)
			ansible.run()
		except Exception:
			log_error("Exception While Giving SSH Access", server=self.as_dict())

	def mount_shared_folder(self, client_server: str, using_fs_of_server: str) -> None:
		self._mount_shared_folder_on_client_server(client_server, using_fs_of_server)

		if self.move_benches:
			self._move_benches_to_shared(client_server)

	def attach_volume_and_move_data(
		self, client_server: str, using_fs_of_server: str, share_file_system: bool
	) -> None:
		"""
		Attach an EBS volume to the NFS server for the client sharing their file system,
		or update the volume name on servers using a shared volume.
		"""
		# Get existing volume from the server that is already sharing its fs
		# If using someone elses fs then we don't need to move our data to it
		self.using_volume = (
			self._create_and_attach_volume_on_nfs_server(using_fs_of_server)
			if share_file_system
			else self._get_volume_from_sharing_server(using_fs_of_server)
		)
		# At this point we are ready to share but the benches might not be moved
		if self.share_file_system:
			# Need to give ssh access to the server for rsync to work
			self._allow_ssh_access_to_nfs_server(client_server=client_server)

		self.ready_to_share_file_system = share_file_system
		self.save()

		self.mount_shared_folder(client_server=client_server, using_fs_of_server=using_fs_of_server)


def umount_and_delete_shared_directory_on_client(client_server: str, nfs_server: str, shared_directory: str):
	client_server: Server = frappe.get_cached_doc("Server", client_server)
	nfs_server_private_ip = frappe.db.get_value("NFS Server", nfs_server, "private_ip")
	try:
		ansible = Ansible(
			playbook="umount_and_cleanup_shared.yml",
			server=client_server,
			user=client_server._ssh_user(),
			port=client_server._ssh_port(),
			variables={
				"nfs_server_private_ip": nfs_server_private_ip,
				"shared_directory": f"/home/frappe/nfs/{shared_directory}",
			},
		)
		ansible.run()
	except Exception:
		log_error("Exception While Cleaning Up Shared Directory")


def detach_umount_and_delete_volume_on_nfs(nfs_server: str, volume_id: str, shared_directory: str):
	virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", nfs_server)

	try:
		virtual_machine.detach(volume_id)
		virtual_machine.delete_volume(volume_id)
	except Exception:
		pass  # Generally throws unable to detach volume, but the volume is detached

	nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", nfs_server)

	try:
		ansible = Ansible(
			playbook="umount_volume_nfs_server.yml",
			server=nfs_server,
			user=nfs_server._ssh_user(),
			port=nfs_server._ssh_port(),
			variables={
				"shared_directory": f"/home/frappe/nfs/{shared_directory}",
			},
		)
		ansible.run()
	except Exception:
		log_error("Exception While Cleaning Up NFS Server")
