# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.utils import log_error

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot import VirtualDiskSnapshot
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


class PhysicalBackupRestoration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.physical_backup_restoration_step.physical_backup_restoration_step import (
			PhysicalBackupRestorationStep,
		)

		destination_database: DF.Data
		destination_server: DF.Link
		disk_snapshot: DF.Link
		site: DF.Link
		site_backup: DF.Link | None
		source_database: DF.Data
		status: DF.Literal["Scheduled", "Pending", "Running", "Success", "Failure"]
		steps: DF.Table[PhysicalBackupRestorationStep]
		volume: DF.Data | None
	# end: auto-generated types

	@property
	def next_step(self) -> PhysicalBackupRestorationStep | None:
		"""Get next step to execute or update."""
		return find(self.steps, lambda step: step.status in ["Pending", "Running"])

	def validate(self):
		if self.is_new():
			snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
			server: DatabaseServer = frappe.get_doc("Database Server", self.destination_server)
			if server.provider != "AWS EC2":
				frappe.throw("Only AWS provider is supported currently.")
			virtual_machine: VirtualMachine = frappe.get_doc("Virtual Machine", snapshot.virtual_machine)

			# validate snapshot should be on same region
			if snapshot.region != virtual_machine.region:
				frappe.throw("Snapshot and server should be in same region.")

			# validate snapshot status
			if snapshot.status not in ("Pending", "Completed"):
				frappe.throw("Snapshot status should be Pending or Completed.")

	def after_insert(self):
		steps = [
			{
				"step_title": self.wait_for_pending_snapshot_to_be_completed.__doc__,
				"method_name": self.wait_for_pending_snapshot_to_be_completed.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.create_volume_from_snapshot.__doc__,
				"method_name": self.create_volume_from_snapshot.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.wait_for_volume_to_be_available.__doc__,
				"method_name": self.wait_for_volume_to_be_available.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.attach_volume_to_instance.__doc__,
				"method_name": self.attach_volume_to_instance.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.mount_volume_to_instance.__doc__,
				"method_name": self.mount_volume_to_instance.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.restore_database.__doc__,
				"method_name": self.restore_database.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.unmount_volume_from_instance.__doc__,
				"method_name": self.unmount_volume_from_instance.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.detach_volume_from_instance.__doc__,
				"method_name": self.detach_volume_from_instance.__name__,
				"status": "Pending",
			},
			{
				"step_title": self.delete_volume.__doc__,
				"method_name": self.delete_volume.__name__,
				"status": "Pending",
			},
		]
		for step in steps:
			self.append("steps", step)
		self.save()

	def wait_for_pending_snapshot_to_be_completed(self):
		"""Wait for pending snapshot to be completed"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		snapshot.sync()

		if snapshot.status == "Completed":
			self.status = "Pending"
			self.save()

		elif snapshot.status != "Pending":
			self.update_next_step_status("Failure")

	def create_volume_from_snapshot(self):
		"""Create volume from snapshot"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		try:
			self.volume = snapshot.create_volume_from_snapshot()
			self.update_next_step_status("Success")
			self.run_next_step()

		except Exception as e:
			self.update_next_step_status("Failure")
			log_error("Error while creating volume from snapshot", data=e)
		self.save()

	def wait_for_volume_to_be_available(self):
		"""Wait for volume to be available"""
		pass

	def attach_volume_to_instance(self):
		"""Attach volume to instance"""
		pass

	def mount_volume_to_instance(self):
		"""Mount volume to instance"""
		pass

	def restore_database(self):
		"""Restore database"""
		pass

	def unmount_volume_from_instance(self):
		"""Unmount volume from instance"""
		pass

	def detach_volume_from_instance(self):
		"""Detach volume from instance"""
		pass

	def delete_volume(self):
		"""Delete volume"""
		pass

	def update_next_step_status(self, status: str):
		self.next_step.status = status
		if status == "Failure":
			self.status = "Failure"
		self.save()

	def run_next_step(self):
		self.status = "Running"

		next_step = self.next_step
		if not next_step:
			self.status = "Success"
			self.save()
			return

		getattr(self, next_step.method_name)()

		self.save()
