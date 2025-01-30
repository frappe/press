# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import os
import time
from enum import Enum
from typing import TYPE_CHECKING, Callable

import frappe
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from press.press.doctype.physical_backup_restoration_step.physical_backup_restoration_step import (
		PhysicalBackupRestorationStep,
	)
	from press.press.doctype.virtual_disk_snapshot.virtual_disk_snapshot import VirtualDiskSnapshot
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

StepStatus = Enum("StepStatus", ["Pending", "Running", "Skipped", "Success", "Failure"])


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
		disk_snapshot: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		job: DF.Link | None
		mount_point: DF.Data | None
		restore_specific_tables: DF.Check
		site: DF.Link
		site_backup: DF.Link
		source_database: DF.Data
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[PhysicalBackupRestorationStep]
		tables_to_restore: DF.JSON | None
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
		SyncStep = False
		AsyncStep = True
		GeneralStep = False
		CleanupStep = True
		methods = [
			(self.wait_for_pending_snapshot_to_be_completed, Wait, SyncStep, GeneralStep),
			(self.create_volume_from_snapshot, NoWait, SyncStep, GeneralStep),
			(self.wait_for_volume_to_be_available, Wait, SyncStep, GeneralStep),
			(self.attach_volume_to_instance, NoWait, SyncStep, GeneralStep),
			(self.create_mount_point, NoWait, SyncStep, GeneralStep),
			(self.mount_volume_to_instance, NoWait, SyncStep, GeneralStep),
			(self.change_permission_of_backup_directory, NoWait, SyncStep, GeneralStep),
			(self.change_permission_of_database_directory, NoWait, SyncStep, GeneralStep),
			(self.restore_database, Wait, AsyncStep, GeneralStep),
			(self.rollback_permission_of_database_directory, NoWait, SyncStep, CleanupStep),
			(self.unmount_volume_from_instance, NoWait, SyncStep, CleanupStep),
			(self.delete_mount_point, NoWait, SyncStep, CleanupStep),
			(self.detach_volume_from_instance, NoWait, SyncStep, CleanupStep),
			(self.wait_for_volume_to_be_detached, Wait, SyncStep, CleanupStep),
			(self.delete_volume, NoWait, SyncStep, CleanupStep),
		]

		steps = []
		for method, wait_for_completion, is_async, is_cleanup_step in methods:
			steps.append(
				{
					"step": method.__doc__,
					"method": method.__name__,
					"wait_for_completion": wait_for_completion,
					"is_async": is_async,
					"is_cleanup_step": is_cleanup_step,
				}
			)
		return steps

	def before_insert(self):
		self.validate_aws_only()
		self.set_disk_snapshot()
		self.validate_snapshot_region()
		self.validate_snapshot_status()
		self.cleanup_restorable_tables()

	def after_insert(self):
		self.set_mount_point()
		self.add_steps()
		self.save()

	def on_update(self):
		if self.has_value_changed("status") and self.status in ["Success", "Failure"]:
			from press.press.doctype.site_update.site_update import (
				process_physical_backup_restoration_status_update,
			)

			process_physical_backup_restoration_status_update(self.name)

	def validate_aws_only(self):
		server_provider = frappe.db.get_value("Database Server", self.destination_server, "provider")
		if server_provider != "AWS EC2":
			frappe.throw("Only AWS provider is supported currently.")

	def set_disk_snapshot(self):
		if not self.disk_snapshot:
			self.disk_snapshot = frappe.get_value("Site Backup", self.site_backup, "database_snapshot")
			if not self.disk_snapshot:
				frappe.throw("Disk Snapshot is not available in site backup")

	def validate_snapshot_region(self):
		snapshot_region = frappe.db.get_value("Virtual Disk Snapshot", self.disk_snapshot, "region")
		if snapshot_region != self.virtual_machine.region:
			frappe.throw("Snapshot and server should be in same region.")

	def validate_snapshot_status(self):
		snapshot_status = frappe.db.get_value("Virtual Disk Snapshot", self.disk_snapshot, "status")
		if snapshot_status not in ("Pending", "Completed"):
			frappe.throw("Snapshot status should be Pending or Completed.")

	def cleanup_restorable_tables(self):
		if not self.restore_specific_tables:
			self.tables_to_restore = "[]"
			return

		# If restore_specific_tables is checked, raise error if tables_to_restore is empty
		if not self.tables_to_restore:
			frappe.throw("You must provide at least one table to restore.")

		tables_to_restore_list = json.loads(self.tables_to_restore)
		site_backup = frappe.get_doc("Site Backup", self.site_backup)
		existing_tables_in_backup = set(
			json.loads(site_backup.innodb_tables) + json.loads(site_backup.myisam_tables)
		)
		filtered_tables_to_restore_list = [
			table for table in tables_to_restore_list if table in existing_tables_in_backup
		]
		self.tables_to_restore = json.dumps(filtered_tables_to_restore_list)

	def set_mount_point(self):
		self.mount_point = f"/mnt/{self.name}"

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
		status = self.virtual_machine.get_state_of_volume(self.volume)
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

	def create_mount_point(self) -> StepStatus:
		"""Create mount point"""
		result = self.ansible_run(f"mkdir -p {self.mount_point}")
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def mount_volume_to_instance(self) -> StepStatus:  # noqa: C901
		"""Mount volume to instance"""

		"""
		> Find out the disk name

		If the disk name is /dev/sdg, it might be renamed to /dev/xvdg in the instance.

		Next, If the volume was created from a snapshot of root volume, the volume will have multiple partitions.

		> lsblk --json -o name,fstype,type,label,serial

		{
			"blockdevices":[
				{ "name":"loop0", "fstype":null, "type": "loop", "label": null },
				{ "name":"loop1", "fstype":null, "type": "loop", "label": null },
				{ "name":"loop2", "fstype":null, "type": "loop", "label": null },
				{ "name":"loop3", "fstype":null, "type": "loop", "label": null },
				{ "name":"loop4", "fstype":null, "type": "loop", "label": null },
				{
					"name":"xvda","fstype":null, "type": "disk", "label": null,
					"children":[
						{
							"name":"xvda1",
							"fstype":"ext4",
							"type":"part",
							"label":"cloudimg-rootfs"
						},
						{
							"name":"xvda14",
							"fstype":null,
							"type":"part",
							"label":null
						},
						{
							"name":"xvda15",
							"fstype":"vfat",
							"type":"part",
							"label":"UEFI"
						}
					]
				},
				{"name":"nvme0n1", "fstype":null, "type":"disk", "label":null, "serial":"vol0784b4423604486ea",
					"children": [
						{"name":"nvme0n1p1", "fstype":"ext4", "type":"part", "label":"cloudimg-rootfs", "serial":null},
						{"name":"nvme0n1p14", "fstype":null, "type":"part", "label":null, "serial":null},
						{"name":"nvme0n1p15", "fstype":"vfat", "type":"part", "label":"UEFI", "serial":null}
					]
				}
			]
		}

		"""
		result = self.ansible_run("lsblk --json -o name,fstype,type,label,serial")
		if result["status"] != "Success":
			return StepStatus.Failure

		devices_info_str: str = result["output"]
		devices_info = json.loads(devices_info_str)["blockdevices"]

		disk_name = self.device.split("/")[-1]  # /dev/sdf -> sdf

		# If disk name is sdf, it might be possible mounted as xvdf
		# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html#device-name-limits
		possible_disks = [disk_name, "xvd{}".format(disk_name.lstrip("sd")[-1])]
		disk_serial = self.volume.replace("-", "").lower()
		disk_partition_to_mount = None

		for device_info in devices_info:
			if device_info["type"] not in ["disk", "part"]:
				continue

			# Check for nvme disks
			is_disk_found = (
				device_info["name"].startswith("nvme") and device_info.get("serial") == disk_serial
			)
			# check for normal disks
			if not is_disk_found:
				for possible_disk in possible_disks:
					if device_info["name"] == possible_disk:
						is_disk_found = True
						break

			# If disk is not found, then continue to next disk
			if not is_disk_found:
				continue

			# If the volume was created from a snapshot of data volume
			# the volume will have only one partition.
			if device_info["type"] == "part":
				disk_partition_to_mount = "/dev/{}".format(device_info["name"])
				break

			# If the volume was created from a snapshot of root volume
			# the volume will have multiple partitions.
			if device_info["type"] == "disk" and device_info.get("children"):
				children = device_info["children"]
				# try to find the partition with label cloudimg-rootfs
				for child in children:
					if child["label"] == "cloudimg-rootfs":
						disk_partition_to_mount = "/dev/{}".format(child["name"])
						break

			if disk_partition_to_mount:
				break

		if not disk_partition_to_mount:
			self.log_error(
				title="Not able to find disk partition to mount",
				message=f"Disk name: {disk_name}, Possible disks: {possible_disks}",
			)
			return StepStatus.Failure

		mount_response = self.ansible_run(f"mount {disk_partition_to_mount} {self.mount_point}")
		if mount_response["status"] != "Success":
			return StepStatus.Failure
		return StepStatus.Success

	def change_permission_of_backup_directory(self) -> StepStatus:
		"""Change permission of backup files"""
		path = os.path.join(self.mount_point, "var/lib/mysql")
		result = self.ansible_run(f"chmod -R 770 {path}")
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def change_permission_of_database_directory(self) -> StepStatus:
		"""Change permission of database directory"""
		result = self.ansible_run(f"chmod 770 /var/lib/mysql/{self.destination_database}")
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def restore_database(self) -> StepStatus:
		"""Restore database"""
		if not self.job:
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

	def rollback_permission_of_database_directory(self) -> StepStatus:
		"""Rollback permission of database directory"""

		# Docs > https://mariadb.com/kb/en/specifying-permissions-for-schema-data-directories-and-tables/
		# Directory > 700 and File > 660

		result = self.ansible_run(
			f"chmod -R 660 /var/lib/mysql/{self.destination_database} && chmod 700 /var/lib/mysql/{self.destination_database} && chown -R mysql:mysql /var/lib/mysql/{self.destination_database}"
		)
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def unmount_volume_from_instance(self) -> StepStatus:
		"""Unmount volume from instance"""
		if self.get_step_status(self.mount_volume_to_instance) != StepStatus.Success.name:
			return StepStatus.Success
		response = self.ansible_run(f"umount {self.mount_point}")
		if response["status"] != "Success":
			return StepStatus.Failure
		return StepStatus.Success

	def delete_mount_point(self) -> StepStatus:
		"""Delete mount point"""
		if not self.mount_point or not self.mount_point.startswith("/mnt"):
			frappe.throw("Mount point is not valid.")
		# check if mount point was created
		if self.get_step_status(self.create_mount_point) != "Success":
			return StepStatus.Success
		response = self.ansible_run(f"rm -rf {self.mount_point}")
		if response["status"] != "Success":
			return StepStatus.Failure
		return StepStatus.Success

	def detach_volume_from_instance(self) -> StepStatus:
		"""Detach volume from instance"""
		# check if volume was attached
		if not self.volume or self.get_step_status(self.attach_volume_to_instance) != "Success":
			return StepStatus.Success
		state = self.virtual_machine.get_state_of_volume(self.volume)
		if state != "in-use":
			return StepStatus.Success
		self.virtual_machine.detach(self.volume)
		return StepStatus.Success

	def wait_for_volume_to_be_detached(self) -> StepStatus:
		"""Wait for volume to be detached"""
		if not self.volume:
			return StepStatus.Success
		state = self.virtual_machine.get_state_of_volume(self.volume)
		if state in ["available", "deleting", "deleted"]:
			return StepStatus.Success
		if state == "error":
			return StepStatus.Failure
		return StepStatus.Pending

	def delete_volume(self) -> StepStatus:
		"""Delete volume"""
		if (
			not self.volume
			or self.get_step_status(self.create_volume_from_snapshot) != StepStatus.Success.name
		):
			return StepStatus.Success
		state = self.virtual_machine.get_state_of_volume(self.volume)
		if state in ["deleting", "deleted"]:
			return StepStatus.Success
		self.virtual_machine.client().delete_volume(VolumeId=self.volume)
		return StepStatus.Success

	def is_db_files_modified_during_failed_restoration(self):
		if self.status != "Failure":
			return False
		# Check if Restore Database job has created
		if not self.job:
			return False
		# Check if Restore Database job has failed
		job_status = frappe.db.get_value("Agent Job", self.job, "status")
		if job_status == "Failure":
			job_steps = frappe.get_all(
				"Agent Job Step",
				filters={
					"agent_job": self.job,
				},
				fields=["step_name", "status"],
				order_by="creation asc",
			)
			"""
			[
				{'step_name': 'Validate Backup Files', 'status': 'Success'},
				{'step_name': 'Validate Connection to Target Database', 'status': 'Success'},
				{'step_name': 'Warmup MyISAM Files', 'status': 'Success'},
				{'step_name': 'Check and Fix MyISAM Table Files', 'status': 'Success'},
				{'step_name': 'Warmup InnoDB Files', 'status': 'Success'},
				{'step_name': 'Prepare Database for Restoration', 'status': 'Success'},
				{'step_name': 'Create Tables from Table Schema', 'status': 'Success'},
				{'step_name': 'Discard InnoDB Tablespaces', 'status': 'Success'},
				{'step_name': 'Copying InnoDB Table Files', 'status': 'Success'},
				{'step_name': 'Import InnoDB Tablespaces', 'status': 'Success'},
				{'step_name': 'Hold Write Lock on MyISAM Tables', 'status': 'Success'},
				{'step_name': 'Copying MyISAM Table Files', 'status': 'Success'},
				{'step_name': 'Unlock All Tables', 'status': 'Success'}
			]
			"""
			# Check on which step the job has failed
			# Anything on after `Prepare Database for Restoration` is considered as full restoration required
			first_failed_step = None
			for step in job_steps:
				if step["status"] == "Failure":
					first_failed_step = step
					break
			if first_failed_step and first_failed_step["step_name"] in [
				"Create Tables from Table Schema",
				"Discard InnoDB Tablespaces",
				"Copying InnoDB Table Files",
				"Import InnoDB Tablespaces",
				"Hold Write Lock on MyISAM Tables",
				"Copying MyISAM Table Files",
				"Unlock All Tables",
			]:
				return True
		return False

	def get_step_status(self, step_method: Callable) -> str:
		step = self.get_step_by_method(step_method.__name__)
		return step.status if step else "Pending"

	def add_steps(self):
		for step in self.migration_steps:
			step.update({"status": "Pending"})
			self.append("steps", step)

	@frappe.whitelist()
	def execute(self):
		# If restore_specific_tables was provided, but no tables are there to restore, then skip the restore
		if self.restore_specific_tables:
			try:
				restorable_tables = json.loads(self.tables_to_restore)
			except Exception:
				restorable_tables = []
			if len(restorable_tables) == 0:
				self.status = "Success"
				for step in self.steps:
					step.status = "Skipped"
				self.save()
				return
		# Else, continue with the restoration
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
		self.duration = frappe.utils.cint((self.end - self.start).total_seconds())
		self.save()
		self.cleanup()

	def finish(self) -> None:
		self.status = "Success"
		# If any step is failed, then mark the job as failed
		for step in self.steps:
			if step.status == "Failure":
				self.status = "Failure"
		self.end = frappe.utils.now_datetime()
		self.duration = frappe.utils.cint((self.end - self.start).total_seconds())
		self.save()

	@frappe.whitelist()
	def next(self, ignore_version=False) -> None:
		self.status = "Running"
		self.save(ignore_version=ignore_version)
		next_step = self.next_step

		if not next_step:
			# We've executed everything
			self.finish()
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
	def cleanup(self):
		is_cleanup_required = False
		for step in self.steps:
			# Mark the pending non-cleanup steps as skipped
			if not step.is_cleanup_step and step.status == "Pending":
				step.status = "Skipped"

			# Mark the cleanup steps with non-failure status as pending
			if step.is_cleanup_step and step.status != "Failure":
				step.status = "Pending"
				is_cleanup_required = True

		if is_cleanup_required:
			self.next()

	@frappe.whitelist()
	def force_continue(self) -> None:
		first_failed_step: PhysicalBackupRestorationStep = None
		# Mark all failed and skipped steps as pending
		for step in self.steps:
			if step.status in ("Failure", "Skipped"):
				if not first_failed_step:
					first_failed_step = step
				step.status = "Pending"

		# If the job was failed in Restore Database step, then reset the job
		if first_failed_step and first_failed_step.method == self.restore_database.__name__:
			self.job = None
		self.next()

	@frappe.whitelist()
	def force_fail(self) -> None:
		# Mark all pending steps as failure
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Failure"
		self.status = "Failure"
		self.save()

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
			if step.is_async and result == StepStatus.Pending:
				self.save(ignore_version=True)
				return
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

		if step.status == "Failure":
			self.fail()
		else:
			self.next(ignore_version_while_saving)

	def get_step(self, step_name) -> PhysicalBackupRestorationStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None

	def get_step_by_method(self, method_name) -> PhysicalBackupRestorationStep | None:
		for step in self.steps:
			if step.method == method_name:
				return step
		return None

	def ansible_run(self, command):
		inventory = f"{self.virtual_machine.public_ip_address},"
		result = AnsibleAdHoc(sources=inventory).run(command, self.name)[0]
		if result["status"] != "Success":
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
	if job.status in ["Success", "Failure", "Delivery Failure"]:
		doc.next(ignore_version=True)


def get_physical_backup_restoration_steps(name: str) -> list[dict]:
	"""
	{
		"title": "Step Name",
		"status": "Success",
		"output": "Output",
		"stage": "Restore Backup"
	}
	"""
	steps = frappe.get_all(
		"Physical Backup Restoration Step",
		filters={"parent": name},
		fields=["step", "status", "name", "creation"],
		order_by="idx asc",
	)
	job_name = frappe.db.get_value("Physical Backup Restoration", name, "job")
	steps = [
		{
			"title": step["step"],
			"status": step["status"],
			"output": "",
			"stage": "Restore Backup",
			"name": step["name"],
		}
		for step in steps
	]
	job_steps = []
	if job_name:
		job_steps = frappe.get_all(
			"Agent Job Step",
			filters={"agent_job": job_name},
			fields=["output", "step_name", "status", "name"],
			order_by="creation asc",
		)
	if steps:
		index_of_restore_database_step = None
		for index, step in enumerate(steps):
			if step["title"] == "Restore database":
				index_of_restore_database_step = index
				break
		if index_of_restore_database_step is not None:
			job_steps = [
				{
					"title": step.get("step_name"),
					"status": step.get("status"),
					"output": step.get("output"),
					"stage": "Restore Backup",
				}
				for step in job_steps
			]
			steps = (
				steps[:index_of_restore_database_step]
				+ job_steps
				+ steps[index_of_restore_database_step + 1 :]
			)
	return steps
