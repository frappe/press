# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import time
import typing
from enum import Enum

import botocore
import frappe
from frappe.core.utils import find, find_all
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if typing.TYPE_CHECKING:
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine

SUPPORTED_FILESYSTEMS = ["ext4"]


class VirtualDiskResize(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)

		devices: DF.Code | None
		downtime_duration: DF.Duration | None
		downtime_end: DF.Datetime | None
		downtime_start: DF.Datetime | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		expected_disk_size: DF.Int
		filesystem_mount_point: DF.Data | None
		filesystem_type: DF.Data | None
		filesystems: DF.Code | None
		name: DF.Int | None
		new_filesystem_temporary_mount_point: DF.Data | None
		new_filesystem_uuid: DF.Data | None
		new_volume_id: DF.Data | None
		new_volume_iops: DF.Int
		new_volume_size: DF.Int
		new_volume_status: DF.Literal["Unprovisioned", "Attached"]
		new_volume_throughput: DF.Int
		old_filesystem_device: DF.Data | None
		old_filesystem_size: DF.Int
		old_filesystem_used: DF.Int
		old_filesystem_uuid: DF.Data | None
		old_volume_id: DF.Data | None
		old_volume_iops: DF.Int
		old_volume_size: DF.Int
		old_volume_status: DF.Literal["Attached", "Deleted"]
		old_volume_throughput: DF.Int
		scheduled_time: DF.Datetime | None
		service: DF.Data | None
		start: DF.Datetime | None
		status: DF.Literal[
			"Scheduled",
			"Pending",
			"Preparing",
			"Ready",
			"Running",
			"Success",
			"Failure",
		]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_disk_snapshot: DF.Link | None
		virtual_machine: DF.Link
	# end: auto-generated types

	def before_insert(self):
		self.validate_aws_only()
		self.validate_existing_migration()
		self.set_old_volume_attributes()
		self.add_steps()

	def after_insert(self):
		"""Enqueue current volume attribute fetch and volume creation"""
		if not self.scheduled_time:
			self.status = Status.Pending
			self.save()

	def run_prerequisites(self):
		try:
			self.set_filesystem_attributes()
			self.set_new_volume_attributes()
			self.create_new_volume()
			self.status = Status.Ready
		except Exception:
			self.log_error("Virtual Disk Resize Prerequisites Failed")
			self.status = Status.Failure
		self.save()

	def get_lock(self):
		try:
			frappe.get_value("Virtual Machine", self.virtual_machine, "status", for_update=True)
			return True
		except frappe.QueryTimeoutError:
			frappe.db.rollback()
			self.add_comment("Could not acquire lock, the virtual machine seems to be busy.")
			frappe.db.commit()
			return False

	@frappe.whitelist()
	def execute(self):
		if not self.get_lock():
			return

		self.run_prerequisites()
		if self.status != Status.Ready:
			return

		self.start = frappe.utils.now_datetime()
		self.save()
		self.next()

	def add_steps(self):
		for step in self.shrink_steps:
			step.update({"status": StepStatus.Pending})
			self.append("steps", step)

	def validate_aws_only(self):
		if self.machine.cloud_provider != "AWS EC2":
			frappe.throw("This feature is only available for AWS EC2")

	def validate_existing_migration(self):
		if existing := frappe.get_all(
			self.doctype,
			{
				"status": ("in", [Status.Pending, Status.Running]),
				"virtual_machine": self.virtual_machine,
				"name": ("!=", self.name),
			},
			pluck="status",
			limit=1,
		):
			frappe.throw(f"An existing shrink document is already {existing[0].lower()}.")

	def set_filesystem_attributes(self):
		devices = self.fetch_devices()
		if len(devices) != 1:
			frappe.throw("Multiple filesystems found on volume. Can't shrink")

		self.old_filesystem_device = f"/dev/{devices[0]['name']}"

		filesystems = self.fetch_filesystems()

		self.verify_mount_point(devices[0], filesystems[0])
		self.set_old_filesystem_attributes(devices[0], filesystems[0])

		self.devices = json.dumps(devices, indent=2)
		self.filesystems = json.dumps(filesystems, indent=2)
		self.save()

	def fetch_devices(self):
		device_name = self._get_device_from_volume_id(self.old_volume_id)
		command = f"lsblk --json --output name,type,uuid,mountpoint,size,fstype {device_name}"
		output = self.ansible_run(command)["output"]

		"""Sample outputs of the command
		{
			"blockdevices": [
				{"name":"nvme1n1", "type":"disk", "uuid":null, "mountpoint":null, "size":"200G", "fstype":null,
					"children": [
						{"name":"nvme1n1p1", "type":"part", "uuid":"db7f5fbc-cf4b-45ae-985d-11e4b2222934", "mountpoint":"/opt/volumes/mariadb", "size":"199.9G", "fstype":"ext4"},
						{"name":"nvme1n1p14", "type":"part", "uuid":null, "mountpoint":null, "size":"4M", "fstype":null},
						{"name":"nvme1n1p15", "type":"part", "uuid":"1284-3BC2", "mountpoint":null, "size":"106M", "fstype":"vfat"}
					]
				}
			]
		}

		{
			"blockdevices": [
				{"name":"nvme1n1", "type":"disk", "uuid":"d7ed9d71-e496-4ea7-b141-dffb3b1f4884", "mountpoint":"/opt/volumes/mariadb", "size":"20G", "fstype":"ext4"}
			]
		}
		"""
		return self._parse_devices(json.loads(output)["blockdevices"])

	def _get_device_from_volume_id(self, volume_id):
		stripped_id = volume_id.replace("-", "")
		return f"/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_{stripped_id}"

	def _parse_devices(self, devices):
		parsed = []
		for device in devices:
			# We only care about disks and partitions
			if device["type"] != "disk":
				continue

			# Disk has partitions. e.g root volume
			if "children" in device:
				for partition in device["children"]:
					# We only care about data filesystems (ext4)
					# Exclude tmpfs, squashfs, devtmpfs, etc
					if partition["fstype"] not in SUPPORTED_FILESYSTEMS:
						continue
					if partition["type"] == "part":
						parsed.append(partition)
			else:
				# Single partition. e.g data volume
				# We only care about data filesystems (ext4)
				# Exclude tmpfs, squashfs, devtmpfs, etc
				if device["fstype"] not in SUPPORTED_FILESYSTEMS:
					continue
				parsed.append(device)
		return parsed

	def fetch_filesystems(self):
		command = "df -k --sync --local --print-type"
		# Note: ansible run doesn't support --arg=value syntax
		output = self.ansible_run(command)["output"]
		"""Sample output of the command
			Filesystem      Type     1K-blocks    Used Available Use% Mounted on
			/dev/root       ext4       7950536 3179104   4755048  41% /
			devtmpfs        devtmpfs   1961436       0   1961436   0% /dev
			tmpfs           tmpfs      1966204       0   1966204   0% /dev/shm
			tmpfs           tmpfs       393244    1036    392208   1% /run
			tmpfs           tmpfs         5120       0      5120   0% /run/lock
			tmpfs           tmpfs      1966204       0   1966204   0% /sys/fs/cgroup
			/dev/loop0      squashfs     23424   23424         0 100% /snap/amazon-ssm-agent/9882
			/dev/loop1      squashfs     60928   60928         0 100% /snap/core20/2437
			/dev/loop3      squashfs     94208   94208         0 100% /snap/lxd/29631
			/dev/loop2      squashfs     70528   70528         0 100% /snap/core22/1720
			/dev/loop4      squashfs     39680   39680         0 100% /snap/snapd/23546
			/dev/nvme0n1p15 vfat         99801    6427     93374   7% /boot/efi
			/dev/nvme1n1    ext4      20466256 1602488  17798808   9% /opt/volumes/mariadb
			/dev/loop5      squashfs     70528   70528         0 100% /snap/core22/1752
			tmpfs           tmpfs       393240       0    393240   0% /run/user/0
		"""
		return self._parse_filesystems(output)

	def _parse_filesystems(self, raw_filesystems):
		filesystems = []
		for line in raw_filesystems.splitlines()[1:]:  # Skip the header
			if not line:
				continue
			filesystem, type, size, used, available, *_, mountpoint = line.split()
			# We only care about data filesystems (ext4)
			# Exclude tmpfs, squashfs, devtmpfs, etc
			if type not in SUPPORTED_FILESYSTEMS:
				continue

			if filesystem != self.old_filesystem_device:
				continue

			# size and used are number of 1k blocks. We convert them to GB
			# AWS sizing API deals with integer GB
			filesystems.append(
				{
					"filesystem": filesystem,
					"type": type,
					"mount_point": mountpoint,
					"size": frappe.utils.rounded(int(size) / (1024 * 1024), 1),
					"used": frappe.utils.rounded(int(used) / (1024 * 1024), 1),
					"available": frappe.utils.rounded(int(available) / (1024 * 1024), 1),
				}
			)
		return filesystems

	def verify_mount_point(self, device, filesystem):
		if device["mountpoint"] != filesystem["mount_point"]:
			frappe.throw("Device and Filesystem mount point don't match. Can't shrink")

	def reaffirm_old_filesystem_used(self, mountpoint: str):
		"""Reaffirm file system usage using du"""
		output = self.ansible_run(f"du -sx --block-size=1024 {mountpoint}")["output"]

		if not output:
			frappe.throw("Error occurred while fetching filesystem size")

		size = float(output.split()[0])
		return size / 1024**2

	def set_old_filesystem_attributes(self, device, filesystem):
		self.filesystem_mount_point = device["mountpoint"]
		self.filesystem_type = device["fstype"]
		self.old_filesystem_uuid = device["uuid"]
		self.old_filesystem_size = filesystem["size"]
		self.old_filesystem_used = self.reaffirm_old_filesystem_used(device["mountpoint"])

		SERVICES = {
			"/opt/volumes/benches": "docker",
			"/opt/volumes/mariadb": "mariadb",
		}
		self.service = SERVICES.get(self.filesystem_mount_point)

	def set_old_volume_id(self):
		machine = self.machine
		root_volume = machine.get_root_volume()

		volumes = find_all(machine.volumes, lambda v: v.volume_id != root_volume.volume_id)
		if len(volumes) == 0:
			frappe.throw("No additional volumes found. Cannot shrink any volume.")
		elif len(volumes) > 1:
			frappe.throw("Multiple volumes found. Please select the volume to shrink.")

		self.old_volume_id = volumes[0].volume_id

	def set_old_volume_attributes(self):
		if not self.old_volume_id:
			self.set_old_volume_id()

		volume = self.old_volume
		self.old_volume_size = volume.size
		self.old_volume_iops = volume.iops
		self.old_volume_throughput = volume.throughput

	def set_new_volume_attributes(self):
		# Set size and performance attributes for new volume
		# New volume should be roughly 85% full after copying files
		new_size = int(self.old_filesystem_used * 100 / 85)
		self.new_filesystem_size = max(new_size, 10)  # Minimum 10 GB
		self.new_volume_size = max(self.new_filesystem_size, self.expected_disk_size)

		if self.new_volume_size != self.expected_disk_size:
			self.status = Status.Failure
			self.save()
			frappe.throw(
				f"Volume size mismatch expected: {self.expected_disk_size} resolved: {self.new_volume_size}",
				frappe.ValidationError,
			)

		self.new_volume_iops, self.new_volume_throughput = self.get_optimal_performance_attributes()
		self.save()

	def create_new_volume(self):
		# Lock the row to prevent concurrent modifications
		frappe.get_value("Virtual Machine", self.virtual_machine, "status", for_update=True)

		self.new_volume_id = self.machine.attach_new_volume(
			self.new_volume_size,
			iops=self.new_volume_iops,
			throughput=self.new_volume_throughput,
		)
		self.new_volume_status = "Attached"
		self.save()

	def get_optimal_performance_attributes(self):
		MAX_THROUGHPUT = 1000  # 1000 MB/s
		MAX_BLOCK_SIZE = 256  # 256k
		BUFFER = 1.2  # 20% buffer iops for overhead

		throughput = MAX_THROUGHPUT
		iops = int(BUFFER * throughput * 1024 / MAX_BLOCK_SIZE)

		return iops, throughput

	def increase_old_volume_performance(self) -> StepStatus:
		"Increase performance of old volume"
		iops, throughput = self.get_optimal_performance_attributes()
		volume = self.old_volume
		if volume.iops == iops and volume.throughput == throughput:
			return StepStatus.Success
		try:
			self.machine.update_ebs_performance(volume.volume_id, iops, throughput)
		except botocore.exceptions.ClientError as e:
			if e.response.get("Error", {}).get("Code") == "VolumeModificationRateExceeded":
				return StepStatus.Failure
		return StepStatus.Success

	def wait_for_increased_performance(self) -> StepStatus:
		"Wait for increased performance to take effect"
		modification = self.machine.get_volume_modifications(self.old_volume.volume_id)
		if modification and modification["ModificationState"] != "completed":
			return StepStatus.Pending
		return StepStatus.Success

	def format_new_volume(self) -> StepStatus:
		"Format new volume"
		device = self._get_device_from_volume_id(self.new_volume_id)
		output = self.ansible_run(f"mkfs -t {self.filesystem_type} {device}")["output"]
		"""Sample output of the command
		Creating filesystem with 2621440 4k blocks and 655360 inodes
		Filesystem UUID: f82d5b68-765a-4a4c-8fda-67c224726afe
		Superblock backups stored on blocks:
			32768, 98304, 163840, 229376, 294912, 819200, 884736, 1605632

		Allocating group tables: done
		Writing inode tables: done
		Creating journal (16384 blocks): done
		Writing superblocks and filesystem accounting information: done
		"""
		for line in output.splitlines():
			if "UUID" not in line:
				continue
			self.new_filesystem_uuid = line.split()[-1]
		return StepStatus.Success

	def mount_new_volume(self) -> StepStatus:
		"Mount new volume"
		device = self._get_device_from_volume_id(self.new_volume_id)
		self.new_filesystem_temporary_mount_point = "/opt/volumes/resize"
		self.ansible_run(f"mkdir {self.new_filesystem_temporary_mount_point}")
		self.ansible_run(f"mount {device} {self.new_filesystem_temporary_mount_point}")
		return StepStatus.Success

	def stop_service(self) -> StepStatus:
		"Stop service"
		self.downtime_start = frappe.utils.now_datetime()
		if self.service:
			self.ansible_run(f"systemctl stop {self.service}")
		# Filebeat keeps the file open and prevents unmounting
		self.ansible_run("systemctl stop filebeat")
		return StepStatus.Success

	def unmount_bind_mounts(self) -> StepStatus:
		"Unmount bind mounts"
		output = self.ansible_run(
			f"findmnt --json --source {self.old_filesystem_device} --output target,source"
		)["output"]
		mounts = json.loads(output)["filesystems"]
		for mount in mounts:
			if "[/" not in mount["source"]:
				continue
			self.ansible_run(f"umount {mount['target']}")
		return StepStatus.Success

	def snapshot_machine(self) -> StepStatus:
		"Snapshot machine"
		machine = self.machine
		machine.create_snapshots()

		snapshots = frappe.get_all(
			"Virtual Disk Snapshot",
			{
				"name": ("in", machine.flags.created_snapshots),
				"volume_id": self.old_volume_id,
			},
			pluck="name",
		)
		if len(snapshots) == 0:
			frappe.throw("Failed to create a snapshot")

		self.virtual_disk_snapshot = snapshots[0]
		return StepStatus.Success

	def start_copy(self) -> StepStatus:
		"Start copying files"
		server = self.machine.get_server()
		server.copy_files(
			source=self.filesystem_mount_point,
			destination=self.new_filesystem_temporary_mount_point,
			extra_options="-x",
		)
		return StepStatus.Success

	def wait_for_copy(self) -> StepStatus:
		"Wait for files to be copied"
		plays = frappe.get_all(
			"Ansible Play",
			{
				"server": self.machine.get_server().name,
				"play": "Copy Files",
				"creation": (">", self.creation),
			},
			["status"],
			order_by="creation desc",
			limit=1,
		)
		if not plays:
			return StepStatus.Running

		play_status = plays[0].status
		if play_status == "Success":
			return StepStatus.Success
		if play_status in ("Failure", "Unreachable"):
			return StepStatus.Failure

		return StepStatus.Running

	def unmount_old_volume(self) -> StepStatus:
		"Unmount old volume"
		self.ansible_run(f"umount {self.filesystem_mount_point}")
		return StepStatus.Success

	def unmount_new_volume(self) -> StepStatus:
		"Unmount new volume"
		self.ansible_run(f"umount {self.new_filesystem_temporary_mount_point}")
		return StepStatus.Success

	def update_mount(self) -> StepStatus:
		"Mount new volume on old mount point"
		# Mount the new volume using the new UUID
		# Update fstab
		# 	1. Find mount matching the old UUID in fstab
		# 	2. Update UUID for this mountpoint
		# Reference: https://stackoverflow.com/questions/16637799/sed-error-invalid-reference-1-on-s-commands-rhs#comment88576787_16637847
		self.ansible_run(
			f"sed -Ei 's/^UUID\\={self.old_filesystem_uuid}\\s(.*$)/UUID\\={self.new_filesystem_uuid} \\1/g' /etc/fstab"
		)
		self.ansible_run("systemctl daemon-reload")
		return StepStatus.Success

	def start_service(self) -> StepStatus:
		"Start service"
		if self.service:
			self.ansible_run(f"systemctl start {self.service}")

		# We had stopped filebeat, start it again
		self.ansible_run("systemctl start filebeat")
		self.downtime_end = frappe.utils.now_datetime()
		self.downtime_duration = (self.downtime_end - self.downtime_start).total_seconds()
		return StepStatus.Success

	def reduce_performance_of_new_volume(self) -> StepStatus:
		"Reduce performance of new volume"
		self.machine.update_ebs_performance(
			self.new_volume_id, self.old_volume_iops, self.old_volume_throughput
		)
		return StepStatus.Success

	def delete_old_volume(self) -> StepStatus:
		"Delete old volume"
		self.machine.delete_volume(self.old_volume_id)
		self.old_volume_status = "Deleted"
		return StepStatus.Success

	@frappe.whitelist()
	def propagate_volume_id(self) -> StepStatus:
		"Propagate volume id"
		machine = self.machine
		# Only do this if we have 2 volumes (Root and Data)
		# If we have more than 2 volumes, we can't be sure which one is the data volume
		if len(machine.volumes) == 2 and machine.has_data_volume:
			# Clear the volumes list, it'll be repopulated on save
			server = machine.get_server()
			server.mounts = []
			server.save()
		return StepStatus.Success

	def restart_machine(self) -> StepStatus:
		"""Restart machine (in case of f servers)"""
		if self.machine.series != "f":
			return StepStatus.Success

		self.machine.reboot()
		return StepStatus.Success

	@property
	def machine(self) -> "VirtualMachine":
		return frappe.get_doc("Virtual Machine", self.virtual_machine)

	@property
	def old_volume(self):
		return find(self.machine.volumes, lambda v: v.volume_id == self.old_volume_id)

	@property
	def shrink_steps(self):
		Wait, NoWait = True, False
		methods = [
			(self.increase_old_volume_performance, NoWait),
			(self.wait_for_increased_performance, Wait),
			(self.format_new_volume, NoWait),
			(self.mount_new_volume, NoWait),
			(self.stop_service, NoWait),
			(self.unmount_bind_mounts, NoWait),
			(self.snapshot_machine, NoWait),
			(self.start_copy, NoWait),
			(self.wait_for_copy, Wait),
			(self.unmount_old_volume, NoWait),
			(self.unmount_new_volume, NoWait),
			(self.update_mount, NoWait),
			(self.start_service, NoWait),
			(self.reduce_performance_of_new_volume, NoWait),
			(self.delete_old_volume, NoWait),
			(self.propagate_volume_id, NoWait),
			(self.restart_machine, NoWait),
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

	def fail(self) -> None:
		self.status = Status.Failure
		for step in self.steps:
			if step.status in (StepStatus.Pending, StepStatus.Running):
				step.status = StepStatus.Failure
		self.end = frappe.utils.now_datetime()
		self.duration = (self.end - self.start).total_seconds()
		self.save()

	def succeed(self) -> None:
		self.status = Status.Success
		self.end = frappe.utils.now_datetime()
		self.duration = (self.end - self.start).total_seconds()
		self.save()

	@frappe.whitelist()
	def next(self, ignore_version=False) -> None:
		self.status = Status.Running
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
			if step.status in (StepStatus.Failure, StepStatus.Skipped):
				step.status = StepStatus.Pending
		self.next()

	@frappe.whitelist()
	def force_fail(self) -> None:
		# Mark all pending steps as failure
		for step in self.steps:
			if step.status in (StepStatus.Pending, StepStatus.Running):
				step.status = StepStatus.Failure
		self.status = Status.Failure
		self.save()

	@property
	def next_step(self) -> VirtualMachineMigrationStep | None:
		for step in self.steps:
			if step.status in (StepStatus.Pending, StepStatus.Running):
				return step
		return None

	@frappe.whitelist()
	def execute_step(self, step_name):
		step = self.get_step(step_name)

		if not step.start:
			step.start = frappe.utils.now_datetime()

		step.status = StepStatus.Running

		self.save()
		frappe.db.commit()

		ignore_version_while_saving = False
		try:
			step.status = getattr(self, step.method)()
			if step.wait_for_completion:
				step.attempts = step.attempts + 1
				if step.status == StepStatus.Pending:
					# Wait some time before the next run
					ignore_version_while_saving = True
					time.sleep(1)
		except Exception:
			step.status = StepStatus.Failure
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = frappe.utils.now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		ignore_version_while_saving = True
		if step.status == StepStatus.Failure:
			self.fail()
		else:
			self.next(ignore_version_while_saving)

	def get_step(self, step_name) -> VirtualMachineMigrationStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None

	def ansible_run(self, command):
		virtual_machine_ip = frappe.db.get_value("Virtual Machine", self.virtual_machine, "public_ip_address")
		inventory = f"{virtual_machine_ip},"
		result = AnsibleAdHoc(sources=inventory).run(command, self.name, raw_params=True)[0]
		self.add_command(command, result)
		return result

	def add_command(self, command, result):
		pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
		comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
		self.add_comment(text=comment)


# TODO: Change (str, enum.Enum) to enum.StrEnum when migrating to Python 3.11
class StepStatus(str, Enum):
	Pending = "Pending"
	Running = "Running"
	Success = "Success"
	Failure = "Failure"
	Skipped = "Skipped"

	def __str__(self):
		return self.value


class Status(str, Enum):
	Scheduled = "Scheduled"
	Pending = "Pending"
	Preparing = "Preparing"
	Ready = "Ready"
	Running = "Running"
	Success = "Success"
	Failure = "Failure"

	def __str__(self):
		return self.value


def run_scheduled_resizes():
	resize_tasks = frappe.get_all(
		"Virtual Disk Resize",
		filters={"scheduled_time": ("<=", frappe.utils.now()), "status": Status.Scheduled},
		fields=["name", "virtual_machine"],
	)
	for task in resize_tasks:
		frappe.enqueue_doc(
			"Virtual Disk Resize",
			task.name,
			"execute",
			queue="long",
			timeout=2400,
			deduplicate=True,
			job_id=f"resize_job:{task.virtual_machine}",
		)
