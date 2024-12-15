# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import shlex
import subprocess
import time
from enum import Enum
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
		VirtualMachineMigrationStep,
	)

StepStatus = Enum("StepStatus", ["Pending", "Running", "Success", "Failure"])


class VirtualMachineReplacement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)

		copied_virtual_machine: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		image: DF.Link | None
		name: DF.Int | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_machine: DF.Link
	# end: auto-generated types

	def before_insert(self):
		self.validate_aws_only()
		self.validate_existing_replacement()
		self.add_steps()
		self.create_machine_copy()

	def add_steps(self):
		for step in self.replacement_steps:
			step.update({"status": "Pending"})
			self.append("steps", step)

	def create_machine_copy(self):
		# Create a copy of the current machine
		# So we don't lose the instance ids
		self.copied_virtual_machine = f"{self.virtual_machine}-copy"

		if frappe.db.exists("Virtual Machine", self.copied_virtual_machine):
			frappe.delete_doc("Virtual Machine", self.copied_virtual_machine)

		copied_machine = frappe.copy_doc(self.machine)
		copied_machine.insert(set_name=self.copied_virtual_machine)

	def validate_aws_only(self):
		if self.machine.cloud_provider != "AWS EC2":
			frappe.throw("This feature is only available for AWS EC2")

	def validate_existing_replacement(self):
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
			frappe.throw(f"An existing replacement is already {existing[0].lower()}.")

	@property
	def machine(self):
		return frappe.get_doc("Virtual Machine", self.virtual_machine)

	@property
	def copied_machine(self):
		return frappe.get_doc("Virtual Machine", self.copied_virtual_machine)

	@property
	def replacement_steps(self):
		Wait = True
		NoWait = False
		methods = [
			(self.stop_machine, Wait),
			(self.wait_for_machine_to_stop, Wait),
			(self.create_image, NoWait),
			(self.wait_for_image_to_be_available, Wait),
			(self.disable_delete_on_termination_for_all_volumes, NoWait),
			(self.terminate_previous_machine, Wait),
			(self.wait_for_previous_machine_to_terminate, Wait),
			(self.reset_virtual_machine_attributes, NoWait),
			(self.provision_new_machine, NoWait),
			(self.wait_for_machine_to_start, Wait),
			(self.wait_for_machine_to_be_accessible, Wait),
			(self.remove_old_host_key, NoWait),
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

	def create_image(self) -> StepStatus:
		"Create image"
		machine = self.machine
		self.image = machine.create_image(public=False)
		return StepStatus.Success

	def wait_for_image_to_be_available(self) -> StepStatus:
		"Wait for image to be available"
		# We need to make sure image is ready before we proceed
		# Otherwise we might not be able to create a new machine
		image = frappe.get_doc("Virtual Machine Image", self.image)
		image.sync()
		if image.status == "Available":
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
		machine.virtual_machine_image = self.image
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
