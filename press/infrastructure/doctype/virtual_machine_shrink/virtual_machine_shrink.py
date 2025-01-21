# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import time
from enum import Enum

import frappe
from frappe.model.document import Document


class VirtualMachineShrink(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.infrastructure.doctype.virtual_machine_migration_step.virtual_machine_migration_step import (
			VirtualMachineMigrationStep,
		)

		duration: DF.Duration | None
		end: DF.Datetime | None
		name: DF.Int | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		steps: DF.Table[VirtualMachineMigrationStep]
		virtual_machine: DF.Link
	# end: auto-generated types

	def before_insert(self):
		self.validate_aws_only()
		self.validate_existing_migration()
		self.add_steps()

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

	@property
	def machine(self):
		return frappe.get_doc("Virtual Machine", self.virtual_machine)


	@property
	def shrink_steps(self):
		Wait, NoWait = True, False
		methods = [
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

		ignore_version_while_saving	= True
		if step.status == StepStatus.Failure:
			self.fail()
		else:
			self.next(ignore_version_while_saving)

	def get_step(self, step_name) -> VirtualMachineMigrationStep | None:
		for step in self.steps:
			if step.name == step_name:
				return step
		return None


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

