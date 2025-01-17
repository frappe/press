# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import time
from enum import Enum
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot import VirtualDiskSnapshot
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

StepStatus = Enum("StepStatus", ["Pending", "Running", "Success", "Failure"])


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
		job: DF.Link | None
		mount_path: DF.Data | None
		site: DF.Link
		site_backup: DF.Link | None
		source_database: DF.Data
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[PhysicalBackupRestorationStep]
		volume: DF.Data | None
	# end: auto-generated types

	@property
	def virtual_machine(self) -> VirtualMachine:
		"""Get virtual machine of destination server."""
		return frappe.get_doc(
			"Virtual Machine", frappe.get_value("Database Server", self.destination_server, "virtual_machine")
		)

	@property
	def migration_steps(self):
		Wait = True
		NoWait = False
		methods = [
			(self.wait_for_pending_snapshot_to_be_completed, Wait),
			(self.create_volume_from_snapshot, NoWait),
			(self.wait_for_volume_to_be_available, Wait),
			(self.attach_volume_to_instance, NoWait),
			(self.mount_volume_to_instance, NoWait),
			(self.change_permission_of_database_directory, NoWait),
			(self.restore_database, Wait),
			(self.rollback_permission_change_of_database_directory, NoWait),
			(self.unmount_volume_from_instance, NoWait),
			(self.detach_volume_from_instance, NoWait),
			(self.delete_volume, NoWait),
		]

		steps = []
		for method, wait_for_completion in methods:
			steps.append(
				{
					"step": method.__doc__,
					"method": method.__name__,
					"wait_for_completion": wait_for_completion,
				}
			)
		return steps

	def before_insert(self):
		self.validate_aws_only()
		self.validate_snapshot_region()
		self.validate_snapshot_status()

	def after_insert(self):
		self.add_steps()

	def validate_aws_only(self):
		server_provider = frappe.db.get_value("Database Server", self.destination_server, "provider")
		if server_provider != "AWS EC2":
			frappe.throw("Only AWS provider is supported currently.")

	def validate_snapshot_region(self):
		snapshot_region = frappe.db.get_value("Virtual Disk Snapshot", self.disk_snapshot, "region")
		if snapshot_region != self.virtual_machine.region:
			frappe.throw("Snapshot and server should be in same region.")

	def validate_snapshot_status(self):
		snapshot_status = frappe.db.get_value("Virtual Disk Snapshot", self.disk_snapshot, "status")
		if snapshot_status not in ("Pending", "Completed"):
			frappe.throw("Snapshot status should be Pending or Completed.")

	def wait_for_pending_snapshot_to_be_completed(self) -> StepStatus:
		"""Wait for pending snapshot to be completed"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		snapshot.sync()

		if snapshot.status == "Completed":
			return StepStatus.Success
		if snapshot.status == "Pending":
			return StepStatus.Pending
		return StepStatus.Failure

	def create_volume_from_snapshot(self) -> StepStatus:
		"""Create volume from snapshot"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		self.volume = snapshot.create_volume(availability_zone=self.virtual_machine.availability_zone)
		return StepStatus.Success

	def wait_for_volume_to_be_available(self) -> StepStatus:
		"""Wait for volume to be available"""
		status = self.virtual_machine.get_status_of_volume(self.volume)
		# https://docs.aws.amazon.com/ebs/latest/userguide/ebs-describing-volumes.html
		if status == "available":
			return StepStatus.Success
		if status == "creating":
			return StepStatus.Pending
		return StepStatus.Failure

	def attach_volume_to_instance(self) -> StepStatus:
		"""Attach volume to instance"""
		self.device = self.virtual_machine.attach_volume(self.volume)
		return StepStatus.Success

	def mount_volume_to_instance(self) -> StepStatus:  # noqa: C901
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
			return StepStatus.Failure

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
			return StepStatus.Failure

		self.mount_path = "/mnt/{}".format(self.volume.split("-")[-1])
		mount_response = self.ansible_run(f"mount {disk_partition_to_mount} {self.mount_path}")[0]
		if mount_response["status"] != "Success":
			self.add_comment(text=f"Error mounting disk: {mount_response}")
			return StepStatus.Failure
		return StepStatus.Success

	def change_permission_of_database_directory(self) -> StepStatus:
		result = self.ansible_run(f"chmod 770 /var/lib/mysql/{self.database_name}")
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def restore_database(self) -> StepStatus:
		"""Restore database"""
		if not self.site:
			site = frappe.get_doc("Site", self.site)
			agent = Agent(self.destination_server, "Database Server")
			self.job = agent.physical_restore_database(site, self)
			return StepStatus.Pending
		job_status = frappe.db.get_value("Agent Job", self.job, "status")
		if job_status in ["Undelivered", "Running", "Pending"]:
			return StepStatus.Pending
		if job_status == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def rollback_permission_change_of_database_directory(self) -> StepStatus:
		result = self.ansible_run(f"chmod 700 /var/lib/mysql/{self.database_name}")
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def unmount_volume_from_instance(self) -> StepStatus:
		"""Unmount volume from instance"""
		response = self.ansible_run(f"umount {self.mount_path}")[0]
		if response["status"] != "Success":
			return StepStatus.Failure
		return StepStatus.Success

	def detach_volume_from_instance(self) -> StepStatus:
		"""Detach volume from instance"""
		response = self.virtual_machine.detach(self.volume)
		if response["status"] != "Success":
			return StepStatus.Failure
		return StepStatus.Success

	def delete_volume(self) -> StepStatus:
		"""Delete volume"""
		self.virtual_machine.client.delete_volume(VolumeId=self.volume)
		return StepStatus.Success

	def add_steps(self):
		for step in self.migration_steps:
			step.update({"status": "Pending"})
			self.append("steps", step)

	@frappe.whitelist()
	def execute(self):
		self.status = "Running"
		self.start = frappe.utils.now_datetime()
		self.save()
		self.next()

	def fail(self) -> None:
		self.status = "Failure"
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Skipped"
		self.end = frappe.utils.now_datetime()
		self.duration = (self.end - self.start).total_seconds()
		self.save()

	def succeed(self) -> None:
		self.status = "Success"
		self.end = frappe.utils.now_datetime()
		self.duration = (self.end - self.start).total_seconds()
		self.save()

	@frappe.whitelist()
	def next(self, ignore_version=False) -> None:
		self.status = "Running"
		self.save(ignore_version=ignore_version)
		next_step = self.next_step

		if not next_step:
			# We've executed everything
			self.succeed()
			return

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"execute_step",
			step_name=next_step.name,
			enqueue_after_commit=True,
			at_front=True,
		)

	@frappe.whitelist()
	def force_continue(self) -> None:
		# Mark all failed and skipped steps as pending
		for step in self.steps:
			if step.status in ("Failure", "Skipped"):
				step.status = "Pending"
		self.next()

	@frappe.whitelist()
	def force_fail(self) -> None:
		# Mark all pending steps as failure
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Failure"
		self.status = "Failure"

	@property
	def next_step(self) -> PhysicalBackupRestorationStep | None:
		for step in self.steps:
			if step.status == "Pending":
				return step
		return None

	@frappe.whitelist()
	def execute_step(self, step_name):
		step = self.get_step(step_name)

		if not step.start:
			step.start = frappe.utils.now_datetime()
		step.status = "Running"
		ignore_version_while_saving = False
		try:
			result = getattr(self, step.method)()
			step.status = result.name
			if step.wait_for_completion:
				step.attempts = step.attempts + 1
				if result == StepStatus.Pending:
					# Wait some time before the next run
					ignore_version_while_saving = True
					time.sleep(1)
		except Exception:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = frappe.utils.now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure" and not step.ignore_on_failure:
			self.fail()
		else:
			self.next(ignore_version_while_saving)

	def get_step(self, step_name) -> PhysicalBackupRestorationStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None

	def ansible_run(self, command):
		inventory = f"{self.virtual_machine.public_ip_address},"
		result = AnsibleAdHoc(sources=inventory).run(command, self.name)[0]
		self.add_command(command, result)
		return result

	def add_command(self, command, result):
		pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
		comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
		self.add_comment(text=comment)


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
