# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder


class PressWorkflowTest(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		input_a: DF.Int
		input_b: DF.Int
		input_c: DF.Int
		input_d: DF.Int
		input_e: DF.Int
		input_f: DF.Int
	# end: auto-generated types

	def validate(self):
		if not frappe.in_test:
			frappe.throw("PressWorkflowTest doctype can be used only in Unit Tests")

	@flow
	def main_success(self):
		return "success output"

	@flow
	def main_fail(self):
		raise ValueError("mock failure")

	@task
	def sample_task(self):
		return "task done"

	@task
	def sample_failing_task(self):
		raise ValueError("task failed")

	@task
	def sample_nested_task(self):
		return self.sample_task()

	@flow
	def main_with_task(self):
		return self.sample_task()

	@flow
	def main_with_nested_task(self):
		return self.sample_nested_task()

	@flow
	def main_with_failing_task(self):
		return self.sample_failing_task()

	@task
	def add(self, a: int, b: int) -> int:
		return a + b

	@task
	def multiply(self, a: int, b: int) -> int:
		return a * b

	@flow
	def main_with_args_task(self):
		return self.add(self.input_a, self.input_b)

	@task
	def power(self, base: int, exponent: int) -> int:
		"""Raise base to exponent using repeated multiply calls."""
		result = 1
		for i in range(exponent):
			result = self.multiply.with_task_id(f"mult_{i}")(result, base)
		return result

	@flow
	def main_with_task_id_loop(self):
		return self.power(self.input_a, self.input_b)

	@task
	def multiply_passthrough(self, a: int, b: int, task_id: str | None = None) -> int:
		"""Multiply that receives task_id so it can be inspected."""
		print(f"[multiply_passthrough] task_id={task_id}")  # nosemgrep
		return a * b

	@task
	def power_passthrough(self, base: int, exponent: int, task_id: str | None = None) -> int:
		"""Power that forwards its own task_id to nested multiply calls."""
		result = 1
		for i in range(exponent):
			result = self.multiply_passthrough.with_task_id(
				f"{task_id}_mult_{i}" if task_id else f"mult_{i}"
			)(result, base)
		return result

	@flow
	def main_with_task_id_passthrough(self):
		return self.power_passthrough.with_task_id("power")(self.input_a, self.input_b)

	@task
	def noisy_task(self) -> str:
		print("hello from noisy_task")  # nosemgrep
		return "done"

	@flow
	def main_with_noisy_task(self):
		return self.noisy_task()

	@flow
	def main_as_flow(self):
		self.sample_task()
		self.sample_nested_task()
		return "flow done"

	@flow
	def flow_with_args(self, x: int, y: int) -> int:
		return self.add(x, y)

	@flow
	def missing_method_flow(self):
		return "nothing"

	@flow
	def skipped_steps_flow(self):
		# We define it locally but won't call any of the tasks.
		# Alternatively we can conditionally call them.
		if False:
			self.sample_task()
			self.sample_failing_task()
		return "skipped"
