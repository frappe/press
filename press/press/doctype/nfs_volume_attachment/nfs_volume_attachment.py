# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import typing

import frappe
from frappe.model.document import Document

from press.runner import Ansible
from press.utils import log_error

if typing.TYPE_CHECKING:
	from press.press.doctype.nfs_server.nfs_server import NFSServer
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class NFSVolumeAttachment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.nfs_volume_attachment_step.nfs_volume_attachment_step import (
			NFSVolumeAttachmentStep,
		)

		nfs_server: DF.Link
		nfs_volume_attachment_steps: DF.Table[NFSVolumeAttachmentStep]
		primary_server: DF.Link
		secondary_server: DF.Link
		shared_directory: DF.Data | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		volume_id: DF.Data
		volume_size: DF.Int
	# end: auto-generated types

	def validate(self):
		if not self.secondary_server:
			frappe.throw("Please select a primary server that has a secondary server provisioned!")

	def get_steps(self):
		methods = [
			self.increase_old_volume_performance,
			self.wait_for_increased_performance,
			self.format_new_volume,
			self.mount_new_volume,
			self.stop_service,
			self.unmount_bind_mounts,
			self.snapshot_machine,
			self.start_copy,
			self.wait_for_copy,
			self.unmount_old_volume,
			self.unmount_new_volume,
			self.update_mount,
			self.start_service,
			self.reduce_performance_of_new_volume,
			self.delete_old_volume,
			self.propagate_volume_id,
			self.restart_machine,
		]

		steps = []
		for method in methods:
			steps.append({"name": method.__doc__, "status": "Pending"})

		return steps

	def _format_and_mount_fs(self, volume_id: str) -> None:
		"""Create a filesystem from newly mounted volume and mount shared directory on it"""
		nfs_server: NFSServer = frappe.get_cached_doc("NFS Server", self.nfs_server)
		try:
			ansible = Ansible(
				playbook="mount_ebs_on_nfs_server.yml",
				server=nfs_server,  # Mounting on NFS Server
				user=nfs_server._ssh_user(),
				port=nfs_server._ssh_port(),
				variables={
					"shared_directory": f"/home/frappe/nfs/{self.primary_server}",
					"volume_id": volume_id.replace("vol-", ""),
				},
			)
			ansible.run()
		except Exception:
			log_error("Exception While Mounting Volume on NFS Server", server=self.as_dict())

	def attach_volume_on_nfs_server(self, volume_size: int) -> str:
		"""Attach volume on NFS Server"""
		virtual_machine: VirtualMachine = frappe.get_cached_doc("Virtual Machine", self.nfs_server)
		return virtual_machine.attach_new_volume(volume_size, iops=3000, throughput=124, log_activity=False)

	def format_attached_volume(self, volume_id: str):
		self._format_and_mount_fs(volume_id)

	def before_insert(self):
		steps = self.get_steps()
		for step in steps:
			self.append("nfs_volume_attachment_steps", step)

	def after_insert(self): ...
