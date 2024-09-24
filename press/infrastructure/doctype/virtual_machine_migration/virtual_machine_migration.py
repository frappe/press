# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import time
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
		VirtualMachineMigrationStep,
	)


StepStatus = Enum("StepStatus", ["Pending", "Running", "Success", "Failure"])


class VirtualMachineMigration(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)
		from press.infrastructure.doctype.virtual_machine_migration_volume.virtual_machine_migration_volume import (
			VirtualMachineMigrationVolume,
		)

		copied_virtual_machine: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		machine_type: DF.Data
		name: DF.Int | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_machine: DF.Link
		virtual_machine_image: DF.Link
		volumes: DF.Table[VirtualMachineMigrationVolume]
	# end: auto-generated types

	def before_insert(self):
		self.add_steps()
		self.add_volumes()
		self.create_machine_copy()

	def after_insert(self):
		self.execute()

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

	@property
	def machine(self):
		return frappe.get_doc("Virtual Machine", self.virtual_machine)

	@property
	def copied_machine(self):
		return frappe.get_doc("Virtual Machine", self.copied_virtual_machine)

	@property
	def migration_steps(self):
		return []

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
	def next(self, arguments=None) -> None:
		self.status = "Running"
		self.save()
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
		try:
			result = getattr(self, step.method)()
			step.status = result.name
			if step.wait_for_completion:
				step.attempts = step.attempts + 1
				if result == StepStatus.Pending:
					# Wait some time before the next run
					time.sleep(1)
		except Exception:
			step.status = "Failure"
			step.traceback = frappe.get_traceback(with_context=True)

		step.end = frappe.utils.now_datetime()
		step.duration = (step.end - step.start).total_seconds()

		if step.status == "Failure":
			self.fail()
		else:
			self.next()

	def get_step(self, step_name) -> VirtualMachineMigrationStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None
