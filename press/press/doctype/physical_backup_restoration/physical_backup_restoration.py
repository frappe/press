# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import json
import os
import time
from enum import Enum
from typing import TYPE_CHECKING

import frappe
import frappe.utils
from frappe.model.document import Document

from press.agent import Agent
from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc
from press.press.doctype.physical_restoration_test.physical_restoration_test import trigger_next_restoration
from press.utils import log_error

if TYPE_CHECKING:
	from collections.abc import Callable

	from press.press.doctype.physical_backup_restoration_step.physical_backup_restoration_step import (
		PhysicalBackupRestorationStep,
	)
	from press.press.doctype.site.site import Site
	from press.press.doctype.site_backup.site_backup import SiteBackup
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

		cleanup_completed: DF.Check
		deactivate_site_during_restoration: DF.Check
		destination_database: DF.Data
		destination_server: DF.Link
		device: DF.Data | None
		disk_snapshot: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		is_failure_resolved: DF.Check
		job: DF.Link | None
		log_ansible_output: DF.Check
		mount_point: DF.Data | None
		physical_restoration_test: DF.Data | None
		restore_specific_tables: DF.Check
		site: DF.Link
		site_backup: DF.Link
		source_database: DF.Data
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Scheduled", "Running", "Success", "Failure"]
		steps: DF.Table[PhysicalBackupRestorationStep]
		tables_to_restore: DF.JSON | None
		volume: DF.Data | None
	# end: auto-generated types

	@property
	def virtual_machine_name(self) -> str:
		return frappe.get_value("Database Server", self.destination_server, "virtual_machine")

	@property
	def virtual_machine(self) -> VirtualMachine:
		"""Get virtual machine of destination server."""
		return frappe.get_doc("Virtual Machine", self.virtual_machine_name)

	@property
	def migration_steps(self):
		SyncStep = False
		AsyncStep = True
		GeneralStep = False
		CleanupStep = True
		Wait = True
		NoWait = False
		methods = [
			(self.wait_for_pending_snapshot_to_be_completed, AsyncStep, NoWait, GeneralStep),
			(self.create_volume_from_snapshot, SyncStep, NoWait, GeneralStep),
			(self.wait_for_volume_to_be_available, SyncStep, Wait, GeneralStep),
			(self.attach_volume_to_instance, SyncStep, NoWait, GeneralStep),
			(self.create_mount_point, SyncStep, NoWait, GeneralStep),
			(self.mount_volume_to_instance, SyncStep, NoWait, GeneralStep),
			(self.allow_user_to_modify_db_files_permissions, SyncStep, NoWait, GeneralStep),
			(self.change_permission_of_backup_directory, SyncStep, NoWait, GeneralStep),
			(self.change_permission_of_database_directory, SyncStep, NoWait, GeneralStep),
			(self.restore_database, AsyncStep, NoWait, GeneralStep),
			(self.rollback_permission_of_database_directory, SyncStep, NoWait, CleanupStep),
			(self.unmount_volume_from_instance, SyncStep, NoWait, CleanupStep),
			(self.delete_mount_point, SyncStep, NoWait, CleanupStep),
			(self.detach_volume_from_instance, SyncStep, NoWait, CleanupStep),
			(self.wait_for_volume_to_be_detached, SyncStep, Wait, CleanupStep),
			(self.delete_volume, SyncStep, NoWait, CleanupStep),
		]

		if self.deactivate_site_during_restoration:
			methods.insert(0, (self.deactivate_site, AsyncStep, NoWait, GeneralStep))

		steps = []
		for method, is_async, wait_for_completion, is_cleanup_step in methods:
			steps.append(
				{
					"step": method.__doc__,
					"method": method.__name__,
					"is_async": is_async,
					"wait_for_completion": wait_for_completion,
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

			if self.deactivate_site_during_restoration and self.status == "Success":
				self.activate_site()
				frappe.db.set_value("Site", self.site, "status", "Active")

			if self.deactivate_site_during_restoration and self.status == "Failure":
				if self.is_db_files_modified_during_failed_restoration():
					frappe.db.set_value("Site", self.site, "status", "Broken")
				else:
					self.activate_site()
					frappe.db.set_value("Site", self.site, "status", "Active")

			process_physical_backup_restoration_status_update(self.name)

			if self.physical_restoration_test:
				trigger_next_restoration(self.physical_restoration_test)

	def validate_aws_only(self):
		server_provider = frappe.db.get_value("Database Server", self.destination_server, "provider")
		if server_provider != "AWS EC2":
			frappe.throw("Only AWS hosted server is supported currently.")

	def set_disk_snapshot(self):
		if not self.disk_snapshot:
			site_backup: SiteBackup = frappe.get_doc("Site Backup", self.site_backup)
			if not site_backup.physical:
				frappe.throw("Provided site backup is not physical backup.")

			if site_backup.status != "Success" or site_backup.files_availability != "Available":
				frappe.throw("Provided site backup is not available.")

			if not site_backup.database_snapshot:
				frappe.throw("Disk Snapshot is not available in site backup")

			self.disk_snapshot = site_backup.database_snapshot
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

		tables_to_restore = []
		with contextlib.suppress(Exception):
			tables_to_restore = json.loads(self.tables_to_restore)

		# If restore_specific_tables is checked, raise error if tables_to_restore is empty
		if not tables_to_restore:
			frappe.throw("You must provide at least one table to restore.")

	def set_mount_point(self):
		self.mount_point = f"/mnt/{self.name}"

	def deactivate_site(self):
		"""Deactivate site"""
		deactivate_site_job = frappe.db.get_value(
			"Agent Job",
			{"job_type": "Deactivate Site", "reference_doctype": self.doctype, "reference_name": self.name},
			["name", "status"],
		)
		if not deactivate_site_job:
			site: Site = frappe.get_doc("Site", self.site)
			agent = Agent(site.server)
			agent.deactivate_site(site, reference_doctype=self.doctype, reference_name=self.name)
			# Send `Running` status to the queue
			# So, that the current job can exit for now
			# Once Snapshot status updated, someone will trigger this job again
			return StepStatus.Running

		if deactivate_site_job[1] == "Success":
			return StepStatus.Success

		if deactivate_site_job[1] in ("Failure", "Delivery Failure"):
			return StepStatus.Failure

		return StepStatus.Running

	def wait_for_pending_snapshot_to_be_completed(self) -> StepStatus:
		"""Wait for pending snapshot to be completed"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		with contextlib.suppress(Exception):
			# Don't fail this step due to timestamp mismatch like basic error
			# One background job will trigger this job again anyway
			snapshot.sync()

		if snapshot.status == "Completed":
			return StepStatus.Success
		if snapshot.status == "Pending":
			# Send `Running` status to the queue
			# So, that the current job can exit for now
			# Once Snapshot status updated, someone will trigger this job again
			return StepStatus.Running
		return StepStatus.Failure

	def create_volume_from_snapshot(self) -> StepStatus:
		"""Create volume from snapshot"""
		snapshot: VirtualDiskSnapshot = frappe.get_doc("Virtual Disk Snapshot", self.disk_snapshot)
		self.volume = snapshot.create_volume(
			availability_zone=self.virtual_machine.availability_zone, throughput=300, iops=3000
		)
		self.add_comment(text=f"{self.volume} - Volume Created")
		return StepStatus.Success

	def wait_for_volume_to_be_available(self) -> StepStatus:
		"""Wait for volume to be available"""
		status = self.virtual_machine.get_state_of_volume(self.volume)
		# https://docs.aws.amazon.com/ebs/latest/userguide/ebs-describing-volumes.html
		if status == "available":
			return StepStatus.Success
		if status == "creating":
			return StepStatus.Running
		return StepStatus.Failure

	def attach_volume_to_instance(self) -> StepStatus:
		"""Attach volume to instance"""
		# Used `for_update` to take lock on the record to avoid race condition
		# and make this step failure due to VersionMismatch or TimestampMismatchError
		virtual_machine: VirtualMachine = frappe.get_doc(
			"Virtual Machine", self.virtual_machine_name, for_update=True
		)
		self.device = virtual_machine.attach_volume(self.volume, is_temporary_volume=True)
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

		> lsblk --json -o name,fstype,type,label,serial,size -b

		> Dummy output

		{
			"blockdevices":[
				{ "name":"loop0", "fstype":null, "type": "loop", "label": null, "size": 16543383 },
				{ "name":"loop1", "fstype":null, "type": "loop", "label": null, "size": 16543383 },
				{ "name":"loop2", "fstype":null, "type": "loop", "label": null, "size": 16543383 },
				{ "name":"loop3", "fstype":null, "type": "loop", "label": null, "size": 16543383 },
				{ "name":"loop4", "fstype":null, "type": "loop", "label": null, "size": 16543383 },
				{
					"name":"xvda","fstype":null, "type": "disk", "label": null, "size": 4294966784
					"children":[
						{
							"name":"xvda1",
							"fstype":"ext4",
							"type":"part",
							"label":"cloudimg-rootfs",
							"size": 4294966784
						},
						{
							"name":"xvda14",
							"fstype":null,
							"type":"part",
							"label":null,
							"size": 123345
						},
						{
							"name":"xvda15",
							"fstype":"vfat",
							"type":"part",
							"label":"UEFI",
							"size": 124553
						}
					]
				},
				{"name":"nvme0n1", "fstype":null, "type":"disk", "label":null, "serial":"vol0784b4423604486ea", "size": 4294966784
					"children": [
						{"name":"nvme0n1p1", "fstype":"ext4", "type":"part", "label":"cloudimg-rootfs", "serial":null, "size": 4123906784},
						{"name":"nvme0n1p14", "fstype":null, "type":"part", "label":null, "serial":null "size": 234232},
						{"name":"nvme0n1p15", "fstype":"vfat", "type":"part", "label":"UEFI", "serial":null, "size": 124553}
					]
				}
			]
		}

		"""
		result = self.ansible_run("lsblk --json -o name,fstype,type,label,serial,size -b")
		if result["status"] != "Success":
			return StepStatus.Failure

		devices_info_str: str = result["output"]
		devices_info = json.loads(devices_info_str)["blockdevices"]

		assert self.device is not None, "Device is not set"
		disk_name = self.device.split("/")[-1]  # /dev/sdf -> sdf

		# If disk name is sdf, it might be possible mounted as xvdf
		# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html#device-name-limits
		possible_disks = [disk_name, "xvd{}".format(disk_name.lstrip("sd")[-1])]

		assert self.volume is not None, "Volume is not set"
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

			if device_info["type"] == "disk":
				children = device_info.get("children", [])
				if len(children) == 0:
					# Disk doesn't have any partitions, mount the disk directly
					disk_partition_to_mount = "/dev/{}".format(device_info["name"])
				else:
					# Disk has multiple partitions, so find the correct partition
					largest_partition_size = 1073741824  # 1GB | Disk partition should be larger than 1GB
					largest_partition = None
					# try to find the partition with label cloudimg-rootfs or old-rootfs
					for child in children:
						if child["size"] > largest_partition_size:
							largest_partition_size = child["size"]
							largest_partition = child["name"]

						if child["label"] == "cloudimg-rootfs" or child["label"] == "old-rootfs":
							disk_partition_to_mount = "/dev/{}".format(child["name"])
							break

					# If the partitions are not labeled, try to find largest partition
					if not disk_partition_to_mount and largest_partition is not None:
						disk_partition_to_mount = f"/dev/{largest_partition}"
						break

			if disk_partition_to_mount:
				break

		if not disk_partition_to_mount:
			self.log_error(
				title="Not able to find disk partition to mount",
				message=f"Disk name: {disk_name}, Possible disks: {possible_disks} or with serial {disk_serial}",
			)
			return StepStatus.Failure

		mount_response = self.ansible_run(f"mount {disk_partition_to_mount} {self.mount_point}")
		if mount_response["status"] != "Success":
			return StepStatus.Failure
		return StepStatus.Success

	def allow_user_to_modify_db_files_permissions(self) -> StepStatus:
		"""Allow user to modify db files permissions"""

		result = self.ansible_run(
			r'echo "frappe ALL=(ALL) NOPASSWD: /bin/chown mysql\:mysql /var/lib/mysql/*/*" > /etc/sudoers.d/frappe-mysql',
			raw_params=True,
		)
		if result["status"] == "Success":
			return StepStatus.Success
		return StepStatus.Failure

	def change_permission_of_backup_directory(self) -> StepStatus:
		"""Change permission of backup files"""
		assert self.mount_point is not None, "Mount point is not set"
		base_path = os.path.join(self.mount_point, "var/lib/mysql")
		result = self.ansible_run(f"chmod 777 {base_path}")
		if result["status"] == "Success":
			db_path = os.path.join(self.mount_point, "var/lib/mysql", self.source_database)
			result = self.ansible_run(f"chmod -R 777 {db_path}")
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
			return StepStatus.Running
		job_status = frappe.db.get_value("Agent Job", self.job, "status")
		if job_status in ["Undelivered", "Running", "Pending"]:
			return StepStatus.Running
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

		# Used `for_update` to take lock on the record to avoid race condition
		# and make this step failure due to VersionMismatch or TimestampMismatchError
		virtual_machine: VirtualMachine = frappe.get_doc(
			"Virtual Machine", self.virtual_machine_name, for_update=True
		)
		virtual_machine.detach(self.volume)
		return StepStatus.Success

	def wait_for_volume_to_be_detached(self) -> StepStatus:
		"""Wait for volume to be detached"""
		if not self.volume:
			return StepStatus.Success
		state = self.virtual_machine.get_state_of_volume(self.volume)
		if state in ["available", "deleting", "deleted"]:
			with contextlib.suppress(Exception):
				self.virtual_machine.sync()
			return StepStatus.Success
		if state == "error":
			return StepStatus.Failure
		return StepStatus.Running

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
		self.add_comment(text=f"{self.volume} - Volume Deleted")
		return StepStatus.Success

	def activate_site(self):
		"""Activate site"""
		site: Site = frappe.get_doc("Site", self.site)
		agent = Agent(site.server)
		agent.activate_site(site, reference_doctype=self.doctype, reference_name=self.name)

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
		if self.status == "Scheduled":
			frappe.msgprint("Restoration is already in Scheduled state. It will be executed soon.")
			return
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
		# Just set to scheduled, scheduler will pick it up
		self.status = "Scheduled"
		self.start = frappe.utils.now_datetime()
		self.save()

	def fail(self, save: bool = True) -> None:
		self.status = "Failure"
		for step in self.steps:
			if step.status == "Pending":
				step.status = "Skipped"
		self.end = frappe.utils.now_datetime()
		self.duration = frappe.utils.cint((self.end - self.start).total_seconds())
		if save:
			self.save(ignore_version=True)
		self.cleanup()

	def finish(self) -> None:
		# if status is already Success or Failure, then don't update the status and durations
		if self.status not in ("Success", "Failure"):
			self.status = "Success" if self.is_restoration_steps_successful() else "Failure"
			self.end = frappe.utils.now_datetime()
			self.duration = frappe.utils.cint((self.end - self.start).total_seconds())

		self.cleanup_completed = self.is_cleanup_steps_successful()
		self.save()

	@frappe.whitelist()
	def next(self) -> None:
		if self.status != "Running" and self.status not in ("Success", "Failure"):
			self.status = "Running"
			self.save(ignore_version=True)

		next_step_to_run = None

		# Check if current_step is running
		current_running_step = self.current_running_step
		if current_running_step:
			next_step_to_run = current_running_step
		elif self.next_step:
			next_step_to_run = self.next_step

		if not next_step_to_run:
			# We've executed everything
			self.finish()
			return

		if next_step_to_run.method == self.rollback_permission_of_database_directory.__name__:
			# That means `Restore Database` step has been executed
			self.finish()

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"execute_step",
			step_name=next_step_to_run.name,
			enqueue_after_commit=True,
			deduplicate=next_step_to_run.wait_for_completion
			is False,  # Don't deduplicate if wait_for_completion is True
			job_id=f"physical_restoration||{self.name}||{next_step_to_run.name}",
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

	@frappe.whitelist(allow_guest=True)
	def retry(self):
		# Check if all the cleanup steps are completed
		for step in self.steps:
			if not step.is_cleanup_step:
				continue
			if step.status not in ["Success", "Skipped"]:
				frappe.throw("Cleanup steps are not completed. Please clean up before retrying.")
		# Reset the states
		self.status = "Scheduled"
		self.start = frappe.utils.now_datetime()
		self.volume = None
		self.end = None
		self.duration = None
		self.job = None
		self.cleanup_completed = False
		for step in self.steps:
			step.status = "Pending"
		self.save(ignore_version=True)

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
	def current_running_step(self) -> PhysicalBackupRestorationStep | None:
		for step in self.steps:
			if step.status == "Running":
				return step
		return None

	@property
	def next_step(self) -> PhysicalBackupRestorationStep | None:
		for step in self.steps:
			if step.status == "Pending":
				return step
		return None

	def is_restoration_steps_successful(self) -> bool:
		return all(step.status == "Success" for step in self.steps if not step.is_cleanup_step)

	def is_cleanup_steps_successful(self) -> bool:
		if self.cleanup_completed:
			return True

		# All the cleanup steps need to be Skipped or Success
		# Anything else means the cleanup steps are not completed
		return all(step.status in ("Skipped", "Success") for step in self.steps if step.is_cleanup_step)

	@frappe.whitelist()
	def execute_step(self, step_name):
		step = self.get_step(step_name)

		if not step.start:
			step.start = frappe.utils.now_datetime()
		try:
			result = getattr(self, step.method)()
			step.status = result.name
			"""
			If the step is async and function has returned Running,
			Then save the document and return

			Some external process will resume the job later
			"""
			if step.is_async and result == StepStatus.Running:
				self.save(ignore_version=True)
				return

			"""
			If the step is sync and function is marked to wait for completion,
			Then wait for the function to complete
			"""
			if step.wait_for_completion and result == StepStatus.Running:
				step.attempts = step.attempts + 1 if step.attempts else 1
				self.save(ignore_version=True)
				time.sleep(1)

		except Exception:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = frappe.utils.now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure":
			self.fail(save=True)
		else:
			self.save(ignore_version=True)
			self.next()

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

	def ansible_run(self, command, raw_params: bool = False):
		db = frappe.db.get_value(
			"Database Server", self.destination_server, ("ip", "private_ip", "cluster"), as_dict=True
		)
		result = AnsibleAdHoc(sources=[db]).run(command, self.name, raw_params=raw_params)[0]
		self.add_command(command, result)
		return result

	def add_command(self, command, result):
		if not self.log_ansible_output:
			return
		pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
		comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
		self.add_comment(text=comment)


def process_scheduled_restorations():  # noqa: C901
	start_time = time.time()
	scheduled_restorations = frappe.get_list(
		"Physical Backup Restoration", filters={"status": "Scheduled"}, pluck="name", order_by="creation asc"
	)
	max_concurrent_restorations = frappe.utils.cint(
		frappe.get_cached_value("Press Settings", "Press Settings", "max_concurrent_physical_restorations")
	)
	db_servers_with_max_running_concurrent_restorations = set()
	db_servers_with_incident = set(
		frappe.db.get_all(
			"Incident",
			filters={
				"resource_type": "Database Server",
				"status": ["in", ["Confirmed", "Acknowledged", "Investigating"]],
			},
			pluck="resource",
		)
	)

	for restoration in scheduled_restorations:
		if time.time() - start_time > 25:
			"""
			The job runs every 30 seconds
			So, if we already took 25 seconds, then we should just stop processing
			and let the next job run
			"""
			break
		try:
			doc: PhysicalBackupRestoration = frappe.get_doc("Physical Backup Restoration", restoration)
			"""
			Avoid to start restoration on server, if DB server has incident
			"""
			if doc.destination_server in db_servers_with_incident:
				continue

			"""
			Check if DB server has `enable_physical_backup` checked
			If not, then skip the restoration
			"""
			if not frappe.utils.cint(
				frappe.db.get_value("Database Server", doc.destination_server, "enable_physical_backup")
			):
				continue

			"""
			Take count of `Success` or `Failure` restorations with cleanup pending on db server
			If there are more than 4 jobs like this, don't start new job.

			Until unless cleanup happens the temporary volumes will be left behind in EBS.
			That can create issues in restorations.
			"""
			if (
				frappe.db.count(
					"Physical Backup Restoration",
					filters={
						"status": ["in", ["Success", "Failure"]],
						"cleanup_completed": 0,
						"destination_server": doc.destination_server,
					},
				)
				> 4
			):
				continue

			"""
			Take count of `Running` restorations on db server
			If count is less than `max_concurrent_restorations`, then start the restoration
			"""
			running_restorations = frappe.db.count(
				"Physical Backup Restoration",
				filters={"status": "Running", "destination_server": doc.destination_server},
			)
			if running_restorations > max_concurrent_restorations:
				db_servers_with_max_running_concurrent_restorations.add(doc.destination_server)
				continue

			if doc.status != "Scheduled":
				continue

			doc.next()
			frappe.db.commit()
		except Exception:
			log_error(title="Physical Backup Restoration Start Error", physical_restoration=restoration)
			frappe.db.rollback()


def process_job_update(job):
	if job.reference_doctype != "Physical Backup Restoration":
		return

	doc: PhysicalBackupRestoration = frappe.get_doc("Physical Backup Restoration", job.reference_name)
	if job.status in ["Success", "Failure", "Delivery Failure"]:
		doc.next()


def process_physical_backup_restoration_deactivate_site_job_update(job):
	if job.reference_doctype != "Physical Backup Restoration":
		return
	if job.status not in ["Success", "Failure", "Delivery Failure"]:
		return
	doc: PhysicalBackupRestoration = frappe.get_doc("Physical Backup Restoration", job.reference_name)
	doc.next()


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
