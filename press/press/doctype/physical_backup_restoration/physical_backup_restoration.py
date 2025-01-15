# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import TYPE_CHECKING

import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
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
		device: DF.Data | None
		disk_snapshot: DF.Link
		mount_path: DF.Data | None
		site: DF.Link
		site_backup: DF.Link | None
		source_database: DF.Data
		status: DF.Literal["Pending", "Waiting For Volume", "Running", "Success", "Failure"]
		steps: DF.Table[PhysicalBackupRestorationStep]
		volume: DF.Data | None
	# end: auto-generated types

	@property
	def next_step(self) -> PhysicalBackupRestorationStep | None:
		"""Get next step to execute or update."""
		return find(self.steps, lambda step: step.status in ["Pending", "Running"])

	@property
	def virtual_machine(self) -> VirtualMachine:
		"""Get virtual machine of destination server."""
		return frappe.get_doc(
			"Virtual Machine", frappe.get_value("Database Server", self.destination_server, "virtual_machine")
		)

	def validate(self):
		if self.is_new():
			snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
			server: DatabaseServer = frappe.get_doc("Database Server", self.destination_server)
			if server.provider != "AWS EC2":
				frappe.throw("Only AWS provider is supported currently.")

			# validate snapshot should be on same region
			if snapshot.region != self.virtual_machine.region:
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
			self.status = "Waiting For Volume"
			self.save()

		elif snapshot.status != "Pending":
			self.update_next_step_status("Failure")

	def create_volume_from_snapshot(self):
		"""Create volume from snapshot"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		try:
			self.volume = snapshot.create_volume(
				snapshot_id=snapshot.snapshot_id, availability_zone=self.virtual_machine.availability_zone
			)
			self.update_next_step_status("Success")  # save
			self.run_next_step()

		except Exception as e:
			self.update_next_step_status("Failure")
			log_error("Error while creating volume from snapshot", data=e)

	def wait_for_volume_to_be_available(self):
		"""Wait for volume to be available"""
		self.virtual_machine.wait_for_volume_to_be_available(self.volume)
		self.update_next_step_status("Success")
		self.run_next_step()

	def attach_volume_to_instance(self):
		"""Attach volume to instance"""
		self.device = self.virtual_machine.attach_volume(self.volume)
		self.update_next_step_status("Success")
		self.run_next_step()

	def mount_volume_to_instance(self):  # noqa: C901
		"""Mount volume to instance"""

		"""
		Find out the disk name

		If the disk name is /dev/sdg, it might be renamed to /dev/xvdg in the instance.

		Next, If the volume was created from a snapshot of root volume, the volume will have multiple partitions like -

		> Volume created from snapshot of root volume
		> lsblk -n -l -o NAME,FSTYPE,LABEL -f /dev/xvdg
		xvdg
		xvdg1  ext4   cloudimg-rootfs
		xvdg14
		xvdg15 vfat   UEFI
		xvdg16 ext4   BOOT

		> Volume created from snapshot of data volume
		> sudo lsblk -n -l -o NAME,FSTYPE,LABEL -f /dev/xvdf
		xvdf ext4
		"""
		disks_info_response = self.ansible_run(
			'lsblk -n -l -o NAME,FSTYPE,LABEL |  awk \'{print $1 "," $2 "," $3}\''
		)[0]
		if disks_info_response["status"] != "Success":
			self.add_comment(text=f"Error getting disks info: {disks_info_response}")
			self.update_next_step_status("Failure")
			return

		disks_info_str: str = disks_info_response["output"]
		disks_info = [x.split(",") for x in disks_info_str.split("\n")]  # [<name>, <fstype>, <label>]

		disk_name = self.device.split("/")[-1]

		# If disk name is sdf, it might be possible mounted as xvdf
		# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html#device-name-limits
		possible_disks = [disk_name, "xvd{}".format(disk_name.split("sd"))]

		disk_partition_to_mount = None
		for device in possible_disks:
			for disk_info in disks_info:
				# If the volume was created from a snapshot of data volume, the volume will have only one partition.
				if disk_info[0] == device and disk_info[1] == "ext4":
					disk_partition_to_mount = f"/dev/{device}"
				# When the volume is created from a snapshot of root volume, the volume will have multiple partitions.
				elif (
					disk_info[0] != device
					and disk_info[0].startswith(device)
					and disk_info[1] == "ext4"
					and disk_info[2] == "cloudimg-rootfs"
				):
					disk_partition_to_mount = f"/dev/{device}1"
				if disk_partition_to_mount:
					break
			if disk_partition_to_mount:
				break

		if not disk_partition_to_mount:
			self.log_error(
				title="Not able to find disk partition to mount",
				message=f"Disk name: {disk_name}, Possible disks: {possible_disks}",
			)
			self.update_next_step_status("Failure")
			return

		self.mount_path = "/mnt/{}".format(self.volume.split("-")[-1])
		mount_response = self.ansible_run(f"mount {disk_partition_to_mount} {self.mount_path}")[0]
		if mount_response["status"] != "Success":
			self.add_comment(text=f"Error mounting disk: {mount_response}")
			self.update_next_step_status("Failure")
			return
		self.update_next_step_status("Success")
		self.run_next_step()

	def restore_database(self):
		"""Restore database"""
		site = frappe.get_doc("Site", self.site)
		agent = Agent(self.destination_server)
		agent.physical_restore_database(site, self)
		self.update_next_step_status("Pending")

	def unmount_volume_from_instance(self):
		"""Unmount volume from instance"""
		response = self.ansible_run(f"umount {self.mount_path}")[0]
		if response["status"] != "Success":
			self.add_comment(text=f"Error unmounting disk: {response}")
			self.update_next_step_status("Failure")
			return
		self.update_next_step_status("Success")

	def detach_volume_from_instance(self):
		"""Detach volume from instance"""
		response = self.virtual_machine.detach(self.volume)
		if response["status"] != "Success":
			self.add_comment(text=f"Error detaching disk: {response}")
			self.update_next_step_status("Failure")
			return
		self.update_next_step_status("Success")

	def delete_volume(self):
		"""Delete volume"""
		self.virtual_machine.client.delete_volume(VolumeId=self.volume)
		self.update_next_step_status("Success")

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

	def ansible_run(self, command):
		inventory = f"{self.virtual_machine.public_ip_address},"
		return AnsibleAdHoc(sources=inventory).run(command, self.name)[0]


def process_job_update(job):
	if job.reference_doctype != "Physical Backup Restoration":
		return

	doc: PhysicalBackupRestoration = frappe.get_doc("Physical Backup Restoration", job.reference_name)
	if doc.next_step.step_title != "Restore database":
		return

	if job.status in ["Failure", "Delivery Failure"]:
		doc.update_next_step_status("Failure")
		doc.add_comment(text=f"Error while restoring database: {job.error}")
	elif job.status == "Success":
		doc.update_next_step_status("Success")
		doc.run_next_step()
	elif job.status == "Running":
		if doc.next_step != "Running":
			doc.update_next_step_status("Running")
