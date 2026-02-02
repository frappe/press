# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
import shlex
import subprocess
import time
from enum import Enum
from typing import TYPE_CHECKING, Literal

import frappe
from frappe.core.utils import find
from frappe.model.document import Document

from press.press.doctype.ansible_console.ansible_console import AnsibleAdHoc

if TYPE_CHECKING:
	from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
		VirtualMachineMigrationStep,
	)
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine


StepStatus = Enum("StepStatus", ["Pending", "Running", "Success", "Failure"])


class VirtualMachineMigration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_migration_bind_mount.virtual_machine_migration_bind_mount import (
			VirtualMachineMigrationBindMount,
		)
		from press.infrastructure.doctype.virtual_machine_migration_mount.virtual_machine_migration_mount import (
			VirtualMachineMigrationMount,
		)
		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)
		from press.infrastructure.doctype.virtual_machine_migration_volume.virtual_machine_migration_volume import (
			VirtualMachineMigrationVolume,
		)

		bind_mounts: DF.Table[VirtualMachineMigrationBindMount]
		copied_virtual_machine: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		machine_type: DF.Data
		mounts: DF.Table[VirtualMachineMigrationMount]
		name: DF.Int | None
		new_plan: DF.Link | None
		parsed_devices: DF.Code | None
		raw_devices: DF.Code | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_machine: DF.Link
		virtual_machine_image: DF.Link
		volumes: DF.Table[VirtualMachineMigrationVolume]
	# end: auto-generated types

	def before_insert(self):
		self.server_type: Literal["Database Server", "Server"] = self.machine.get_server().doctype
		self.validate_aws_only()
		self.validate_existing_migration()
		self.add_steps()
		self.add_volumes()
		self.create_machine_copy()
		self.set_new_plan()

	def after_insert(self):
		self.add_devices()
		self.set_default_mounts()
		self.set_default_bind_mounts()

	def add_devices(self):
		command = "lsblk --json --output name,type,uuid,mountpoint,size,label,fstype"
		output = self.ansible_run(command)["output"]

		"""Sample output of the command
		{
			"blockdevices": [
				{"name":"loop0", "type":"loop", "uuid":null, "mountpoint":"/snap/amazon-ssm-agent/9882", "size":"22.9M", "label":null, "fstype":null},
				{"name":"loop1", "type":"loop", "uuid":null, "mountpoint":"/snap/core20/2437", "size":"59.5M", "label":null, "fstype":null},
				{"name":"loop2", "type":"loop", "uuid":null, "mountpoint":"/snap/core22/1666", "size":"68.9M", "label":null, "fstype":null},
				{"name":"loop3", "type":"loop", "uuid":null, "mountpoint":"/snap/snapd/21761", "size":"33.7M", "label":null, "fstype":null},
				{"name":"loop4", "type":"loop", "uuid":null, "mountpoint":"/snap/lxd/29631", "size":"92M", "label":null, "fstype":null},
				{"name":"nvme0n1", "type":"disk", "uuid":null, "mountpoint":null, "size":"25G", "label":null, "fstype":null,
					"children": [
						{"name":"nvme0n1p1", "type":"part", "uuid":"b8932e17-9ed7-47b7-8bf3-75ff6669e018", "mountpoint":"/", "size":"24.9G", "label":"cloudimg-rootfs", "fstype":"ext4"},
						{"name":"nvme0n1p15", "type":"part", "uuid":"7569-BCF0", "mountpoint":"/boot/efi", "size":"99M", "label":"UEFI", "fstype":"vfat"}
					]
				},
				{"name":"nvme1n1", "type":"disk", "uuid":"41527fb0-f6e9-404e-9dba-0451dfa2195e", "mountpoint":"/opt/volumes/mariadb", "size":"10G", "label":null, "fstype":"ext4"}
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

	def set_default_mounts(self):
		# Set root partition from old machine as the data partition in the new machine

		if self.mounts:
			# We've already set the mounts
			return

		parsed_devices = json.loads(self.parsed_devices)
		device = find(parsed_devices, lambda x: x["mountpoint"] == "/")
		if not device:
			# No root volume found
			return

		if self.server_type == "Server":
			target_mount_point = "/opt/volumes/benches"
			service = "docker"
		elif self.server_type == "Database Server":
			target_mount_point = "/opt/volumes/mariadb"
			service = "mariadb"
		else:
			# Data volumes are only supported for Server and Database Server
			return

		self.append(
			"mounts",
			{
				"uuid": device["uuid"],
				"source_mount_point": device["mountpoint"],
				"target_mount_point": target_mount_point,
				"service": service,
			},
		)
		self.save()

	def set_default_bind_mounts(self):
		# These are the same as Server.set_default_mount_points
		if self.bind_mounts:
			return

		if self.server_type == "Server":
			self.append(
				"bind_mounts",
				{
					"source_mount_point": "/opt/volumes/benches/home/frappe/benches",
					"service": "docker",
					"mount_point_owner": "frappe",
					"mount_point_group": "frappe",
				},
			)
			self.append(
				"bind_mounts",
				{
					"source_mount_point": "/opt/volumes/benches/var/lib/docker",
					"service": "docker",
					"mount_point_owner": "root",
					"mount_point_group": "root",
				},
			)
		elif self.server_type == "Database Server":
			self.append(
				"bind_mounts",
				{
					"source_mount_point": "/opt/volumes/mariadb/var/lib/mysql",
					"service": "mariadb",
					"mount_point_owner": "mysql",
					"mount_point_group": "mysql",
				},
			)
			# Don't worry about /etc/mysql
			# It is going to be owned by root, uid=0 and gid=0 everywhere
		else:
			return

		self.save()

	def add_steps(self):
		for step in self.migration_steps:
			step.update({"status": "Pending"})
			self.append("steps", step)

	def add_volumes(self):
		# Prepare volumes to attach to new machine
		for index, volume in enumerate(self.machine.volumes):
			device_name_index = chr(ord("f") + index)
			self.append(
				"volumes",
				{
					"status": "Unattached",
					"volume_id": volume.volume_id,
					# This is the device name that will be used in the new machine
					# Only needed for the attach_volumes call
					"device_name": f"/dev/sd{device_name_index}",
				},
			)

	def create_machine_copy(self):
		# Create a copy of the current machine
		# So we don't lose the instance ids
		self.copied_virtual_machine = f"{self.virtual_machine}-copy"

		if frappe.db.exists("Virtual Machine", self.copied_virtual_machine):
			frappe.delete_doc("Virtual Machine", self.copied_virtual_machine)

		copied_machine = frappe.copy_doc(self.machine)
		copied_machine.insert(set_name=self.copied_virtual_machine)

	def set_new_plan(self):
		server = self.machine.get_server()

		if not server.plan:
			return

		old_plan = frappe.get_doc("Server Plan", server.plan)
		matching_plans = frappe.get_all(
			"Server Plan",
			{
				# "enabled": True,
				"server_type": old_plan.server_type,
				"cluster": old_plan.cluster,
				"instance_type": self.machine_type,
				"premium": old_plan.premium,
			},
			pluck="name",
			limit=1,
		)
		if matching_plans:
			self.new_plan = matching_plans[0]

	def validate_aws_only(self):
		if self.machine.cloud_provider != "AWS EC2":
			frappe.throw("This feature is only available for AWS EC2")

	def validate_existing_migration(self):
		if existing := frappe.get_all(
			self.doctype,
			{
				"status": ("in", ["Pending", "Running"]),
				"virtual_machine": self.virtual_machine,
				"name": ("!=", self.name),
			},
			pluck="status",
			limit=1,
		):
			frappe.throw(f"An existing migration is already {existing[0].lower()}.")

	@property
	def machine(self) -> VirtualMachine:
		return frappe.get_doc("Virtual Machine", self.virtual_machine)

	@property
	def copied_machine(self) -> VirtualMachine:
		return frappe.get_doc("Virtual Machine", self.copied_virtual_machine)

	@property
	def migration_steps(self):
		Wait = True
		NoWait = False
		methods = [
			(self.update_partition_labels, NoWait),
			(self.stop_machine, Wait),
			(self.wait_for_machine_to_stop, Wait),
			(self.disable_delete_on_termination_for_all_volumes, NoWait),
			(self.terminate_previous_machine, Wait),
			(self.wait_for_previous_machine_to_terminate, Wait),
			(self.reset_virtual_machine_attributes, NoWait),
			(self.provision_new_machine, NoWait),
			(self.wait_for_machine_to_start, Wait),
			(self.attach_volumes, NoWait),
			(self.wait_for_machine_to_be_accessible, Wait),
			(self.remove_old_host_key, NoWait),
			(self.update_mounts, NoWait),
			(self.update_bind_mount_permissions, NoWait),
			(self.update_plan, NoWait),
			(self.update_tls_certificate, NoWait),
		]

		if self.server_type == "Server":
			methods.insert(0, (self.remove_docker_containers, Wait))
			methods.append((self.update_server_platform, Wait))
			methods.append((self.update_agent_ansible, Wait))
			methods.append((self.start_active_benches, Wait))

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

	def update_server_platform(self) -> StepStatus:
		"""Update server platform"""
		if "m6a" in self.machine.machine_type:
			return StepStatus.Success

		server = self.machine.get_server()
		server.platform = "arm64"
		server.save()
		return StepStatus.Success

	def remove_docker_containers(self) -> StepStatus:
		"""Remove docker containers"""
		container_names = frappe.get_all(
			"Bench",
			{"status": "Active", "server": self.machine.name},
			pluck="name",
		)
		if container_names:
			container_names = " ".join(container_names)
			command = f"docker rm -f {container_names}"
			result = self.ansible_run(command)

			if result["status"] != "Success" or result["error"]:
				self.add_comment(text=f"Error stoping docker: {result}")
				return StepStatus.Failure

		return StepStatus.Success

	def update_agent_ansible(self) -> StepStatus:
		"""Update agent on server"""
		server: Server = frappe.get_doc("Server", self.machine.name)
		server._update_agent_ansible()
		return StepStatus.Success

	def start_active_benches(self) -> StepStatus:
		"""Start active benches on the server"""
		server: Server = frappe.get_doc("Server", self.machine.name)
		server.start_active_benches()
		return StepStatus.Success

	def update_partition_labels(self) -> StepStatus:
		"Update partition labels"
		# Ubuntu images have labels for root (cloudimg-rootfs) and efi (UEFI) partitions
		# Remove these labels from the old volume
		# So the new machine doesn't mount these as root or efi partitions
		# Important: Update fstab so we can still boot the old machine
		parsed_devices = json.loads(self.parsed_devices)  # type: ignore[arg-type]
		for device in parsed_devices:
			old_label = device["label"]
			if not old_label:
				continue

			labeler = {"ext4": "e2label", "vfat": "fatlabel"}[device["fstype"]]
			new_label = {"cloudimg-rootfs": "old-rootfs", "UEFI": "OLD-UEFI"}[old_label]
			commands = [
				# Reference: https://wiki.archlinux.org/title/Persistent_block_device_naming#by-label
				f"{labeler} /dev/{device['name']} {new_label}",
				f"sed -i 's/LABEL\\={old_label}/LABEL\\={new_label}/g' /etc/fstab",  # Ansible implementation quirk
			]
			if old_label == "UEFI":
				# efi mounts have dirty bit set. This resets it.
				commands.append(f"fsck -a /dev/{device['name']}")

			for command in commands:
				result = self.ansible_run(command)
				if result["status"] != "Success":
					self.add_comment(text=f"Error updating partition labels: {result}")
					return StepStatus.Failure
		return StepStatus.Success

	def stop_machine(self) -> StepStatus:
		"Stop machine"
		machine = self.machine
		machine.sync()
		if machine.status == "Stopped":
			return StepStatus.Success
		if machine.status == "Pending":
			return StepStatus.Pending
		machine.stop()
		return StepStatus.Success

	def wait_for_machine_to_stop(self) -> StepStatus:
		"Wait for machine to stop"
		# We need to make sure the machine is stopped before we proceed
		machine = self.machine
		machine.sync()
		if machine.status == "Stopped":
			return StepStatus.Success
		return StepStatus.Pending

	def disable_delete_on_termination_for_all_volumes(self) -> StepStatus:
		"Disable Delete-on-Termination for all volumes"
		# After this we can safely terminate the instance without losing any data
		copied_machine = self.copied_machine
		if copied_machine.volumes:
			copied_machine.disable_delete_on_termination_for_all_volumes()
		return StepStatus.Success

	def terminate_previous_machine(self) -> StepStatus:
		"Terminate previous machine"
		copied_machine = self.copied_machine
		if copied_machine.status == "Terminated":
			return StepStatus.Success
		if copied_machine.status == "Pending":
			copied_machine.sync()
			return StepStatus.Pending

		copied_machine.disable_termination_protection()
		copied_machine.reload()
		copied_machine.terminate()
		return StepStatus.Success

	def wait_for_previous_machine_to_terminate(self) -> StepStatus:
		"Wait for previous machine to terminate"
		# Private ip address is released when the machine is terminated
		copied_machine = self.copied_machine
		copied_machine.sync()
		if copied_machine.status == "Terminated":
			return StepStatus.Success
		return StepStatus.Pending

	def reset_virtual_machine_attributes(self) -> StepStatus:
		"Reset virtual machine attributes"
		machine = self.machine
		machine.instance_id = None
		machine.public_ip_address = None
		machine.volumes = []

		# Set new machine image and machine type
		machine.virtual_machine_image = self.virtual_machine_image
		machine.machine_image = None
		machine.machine_type = self.machine_type
		machine.root_disk_size = 10  # Default root disk size for new machines
		machine.has_data_volume = True  # VM Migration always adds a data volume
		machine.save()
		return StepStatus.Success

	def provision_new_machine(self) -> StepStatus:
		"Provision new machine"
		# Create new machine in place. So we retain Name, IP etc.
		self.machine._provision_aws()
		return StepStatus.Success

	def wait_for_machine_to_start(self) -> StepStatus:
		"Wait for new machine to start"
		# We can't attach volumes to a machine that is not running
		machine = self.machine
		machine.sync()
		if machine.status == "Running":
			return StepStatus.Success
		return StepStatus.Pending

	def attach_volumes(self) -> StepStatus:
		"Attach volumes"
		machine = self.machine
		for volume in self.volumes:
			try:
				machine.client().attach_volume(
					InstanceId=machine.instance_id,
					Device=volume.device_name,
					VolumeId=volume.volume_id,
				)
				volume.status = "Attached"
			except Exception as e:
				self.add_comment(text=f"Error attaching volume {volume.volume_id}: {e}")
		machine.sync()
		return StepStatus.Success

	def wait_for_machine_to_be_accessible(self):
		"Wait for machine to be accessible"
		server = self.machine.get_server()
		server.ping_ansible()

		plays = frappe.get_all(
			"Ansible Play",
			{"server": server.name, "play": "Ping Server", "creation": (">", self.creation)},
			["status"],
			order_by="creation desc",
			limit=1,
		)
		if plays and plays[0].status == "Success":
			return StepStatus.Success
		return StepStatus.Pending

	def remove_old_host_key(self) -> StepStatus:
		"Remove old host key"
		command = f"ssh-keygen -R '{self.virtual_machine}'"
		subprocess.check_call(shlex.split(command))
		return StepStatus.Success

	def update_mounts(self) -> StepStatus:
		"Update mounts"
		# Mount the volume using the old UUID
		# Update fstab
		# 	1. Find mount matching the source mount point in fstab
		# 	2. Update UUID for this mountpoint
		AllowFailure, DontAllowFailure = True, False
		for mount in self.mounts:
			escaped_mount_point = mount.target_mount_point.replace("/", "\\/")
			# Reference: https://stackoverflow.com/questions/16637799/sed-error-invalid-reference-1-on-s-commands-rhs#comment88576787_16637847
			commands = [
				(
					f"sed -Ei 's/^UUID\\=.*\\s({escaped_mount_point}\\s.*$)/UUID\\={mount.uuid} \\1/g' /etc/fstab",
					DontAllowFailure,
				),
				("systemctl daemon-reload", DontAllowFailure),
			]
			if mount.service:
				commands.append((f"systemctl start {mount.service}", AllowFailure))
			for command, allow_failure in commands:
				result = self.ansible_run(command)
				if allow_failure == DontAllowFailure and result["status"] != "Success":
					self.add_comment(text=f"Error updating mounts: {result}")
					return StepStatus.Failure

		return StepStatus.Success

	def update_bind_mount_permissions(self) -> StepStatus:
		"Update bind mount permissions"
		# linux uid / gid might not be the same in the new machine
		for mount in self.bind_mounts:
			commands = [
				f"chown -R {mount.mount_point_owner}:{mount.mount_point_group} {mount.source_mount_point}",
				# The dependent service might have failed. Start it
				f"systemctl start {mount.service}",
			]
			for command in commands:
				result = self.ansible_run(command)
				if result["status"] != "Success":
					self.add_comment(text=f"Error updating bind mount permissions: {result}")
					return StepStatus.Failure

		return StepStatus.Success

	def update_plan(self) -> StepStatus:
		"Update plan"
		if self.new_plan:
			server = self.machine.get_server()
			plan = frappe.get_doc("Server Plan", self.new_plan)
			server._change_plan(plan)
		return StepStatus.Success

	def update_tls_certificate(self) -> StepStatus:
		"Update TLS certificate"
		server = self.machine.get_server()
		server.update_tls_certificate()

		plays = frappe.get_all(
			"Ansible Play",
			{"server": server.name, "play": "Setup TLS Certificates", "creation": (">", self.creation)},
			["status"],
			order_by="creation desc",
			limit=1,
		)
		if not plays:
			return StepStatus.Failure
		if plays[0].status == "Success":
			return StepStatus.Success
		return StepStatus.Failure

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
	def next_step(self) -> VirtualMachineMigrationStep | None:
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

		if step.status == "Failure":
			self.fail()
		else:
			self.next(ignore_version_while_saving)

	def get_step(self, step_name) -> VirtualMachineMigrationStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None

	def ansible_run(self, command):
		vm = frappe.db.get_value(
			"Virtual Machine",
			self.virtual_machine,
			("public_ip_address as ip", "private_ip_address as private_ip", "cluster"),
			as_dict=True,
		)
		result = AnsibleAdHoc(sources=[vm]).run(command, self.name)[0]
		self.add_command(command, result)
		return result

	def add_command(self, command, result):
		pretty_result = json.dumps(result, indent=2, sort_keys=True, default=str)
		comment = f"<pre><code>{command}</code></pre><pre><code>{pretty_result}</pre></code>"
		self.add_comment(text=comment)
