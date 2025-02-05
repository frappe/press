# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import time
from enum import Enum

import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

SUPPORTED_FILESYSTEMS = ["ext4"]


class VirtualMachineShrink(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)
		from press.infrastructure.doctype.virtual_machine_shrink_filesystem.virtual_machine_shrink_filesystem import (
			VirtualMachineShrinkFilesystem,
		)
		from press.infrastructure.doctype.virtual_machine_shrink_volume.virtual_machine_shrink_volume import (
			VirtualMachineShrinkVolume,
		)

		duration: DF.Duration | None
		end: DF.Datetime | None
		filesystems: DF.Table[VirtualMachineShrinkFilesystem]
		name: DF.Int | None
		new_volumes: DF.Table[VirtualMachineShrinkVolume]
		old_volumes: DF.Table[VirtualMachineShrinkVolume]
		parsed_devices: DF.Code | None
		parsed_filesystems: DF.Code | None
		raw_devices: DF.Code | None
		raw_filesystems: DF.Code | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_machine: DF.Link
	# end: auto-generated types

	def before_insert(self):
		self.validate_aws_only()
		self.validate_existing_migration()
		self.add_steps()

	def after_insert(self):
		self.add_old_volumes()
		self.add_devices()
		self.add_filesystems()
		self.create_new_volumes()
		self.status = Status.Success
		self.save()

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

	def add_devices(self):
		command = "lsblk --json --output name,type,uuid,mountpoint,size,fstype"
		output = self.ansible_run(command)["output"]

		"""Sample output of the command
		{
			"blockdevices": [
				{"name":"loop0", "type":"loop", "uuid":null, "mountpoint":"/snap/amazon-ssm-agent/9882", "size":"22.9M", "fstype":null},
				{"name":"loop1", "type":"loop", "uuid":null, "mountpoint":"/snap/core20/2437", "size":"59.5M", "fstype":null},
				{"name":"loop2", "type":"loop", "uuid":null, "mountpoint":"/snap/core22/1720", "size":"68.9M", "fstype":null},
				{"name":"loop3", "type":"loop", "uuid":null, "mountpoint":"/snap/lxd/29631", "size":"92M", "fstype":null},
				{"name":"loop4", "type":"loop", "uuid":null, "mountpoint":"/snap/snapd/23546", "size":"38.7M", "fstype":null},
				{"name":"loop5", "type":"loop", "uuid":null, "mountpoint":"/snap/core22/1752", "size":"68.9M", "fstype":null},
				{"name":"nvme0n1", "type":"disk", "uuid":null, "mountpoint":null, "size":"8G", "fstype":null,
					"children": [
						{"name":"nvme0n1p1", "type":"part", "uuid":"b113b841-a1ab-417c-8e6d-a6167e2b26df", "mountpoint":"/", "size":"7.9G", "fstype":"ext4"},
						{"name":"nvme0n1p15", "type":"part", "uuid":"9A05-3AFC", "mountpoint":"/boot/efi", "size":"99M", "fstype":"vfat"}
					]
				},
				{"name":"nvme1n1", "type":"disk", "uuid":"d7ed9d71-e496-4ea7-b141-dffb3b1f4884", "mountpoint":"/opt/volumes/mariadb", "size":"20G", "fstype":"ext4"}
			]
		}"""
		devices = json.loads(output)["blockdevices"]
		self.raw_devices = json.dumps(devices, indent=2)
		self.parsed_devices = json.dumps(self._parse_devices(devices), indent=2)
		self.save()

	def _parse_devices(self, devices):
		parsed = []
		for device in devices:
			# We only care about disks and partitions
			if device["type"] != "disk":
				continue

			# Disk has partitions. e.g root volume
			if "children" in device:
				for partition in device["children"]:
					if partition["type"] == "part":
						parsed.append(partition)
			else:
				# Single partition. e.g data volume
				parsed.append(device)
		return parsed

	def add_filesystems(self):
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
		filesystems = []
		for line in output.splitlines()[1:]:  # Skip the header
			if not line:
				continue
			filesystem, type, size, used, available, *_, mountpoint = line.split()
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

		self.raw_filesystems = json.dumps(filesystems, indent=2)
		parsed_filesystems = self._parse_filesystems(filesystems)
		self.parsed_filesystems = json.dumps(parsed_filesystems, indent=2)
		self.add_filesystems_to_table(parsed_filesystems)
		self.save()

	def _parse_filesystems(self, filesystems):
		parsed = []
		for filesystem in filesystems:
			# We only care about data filesystems (ext4)
			# Exclude tmpfs, squashfs, devtmpfs, etc
			if filesystem["type"] not in SUPPORTED_FILESYSTEMS:
				continue

			parsed.append(filesystem)
		return parsed

	def add_filesystems_to_table(self, filesystems):
		parsed_devices = json.loads(self.parsed_devices)
		mounts = self.machine.get_server().mounts
		for filesystem in filesystems:
			device = find(parsed_devices, lambda d: d["mountpoint"] == filesystem["mount_point"])
			mount = find(mounts, lambda m: m.mount_point == filesystem["mount_point"])

			if not device or not mount:
				continue

			filesystem.update(
				{
					"uuid": device["uuid"],
					"volume_id": mount.volume_id,
				}
			)
			self.append("filesystems", filesystem)

	def add_old_volumes(self):
		machine = self.machine
		root_volume = machine.get_root_volume()
		for volume in machine.volumes:
			if volume.volume_id == root_volume.volume_id:
				continue
			self.append(
				"old_volumes",
				{
					"volume_id": volume.volume_id,
					"status": "Attached",
					"size": volume.size,
				},
			)

	def create_new_volumes(self):
		# Create new volumes for the filesystems
		machine = self.machine
		for filesystem in self.filesystems:
			used_size = filesystem.size - filesystem.available
			# New volume should be roughly 85% full after copying files
			new_size = int(used_size * 100 / 85)
			volume_id = machine.attach_new_volume(new_size)
			self.append(
				"new_volumes",
				{
					"volume_id": volume_id,
					"status": "Attached",
					"size": new_size,
				},
			)

	@property
	def machine(self):
		return frappe.get_doc("Virtual Machine", self.virtual_machine)

	@property
	def shrink_steps(self):
		Wait, NoWait = True, False  # noqa: F841
		methods = []

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

	@frappe.whitelist()
	def execute(self):
		self.status = Status.Running
		self.start = frappe.utils.now_datetime()
		self.save()
		self.next()

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
		result = AnsibleAdHoc(sources=inventory).run(command, self.name)[0]
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
	Pending = "Pending"
	Running = "Running"
	Success = "Success"
	Failure = "Failure"

	def __str__(self):
		return self.value
