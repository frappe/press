# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import io
from contextlib import redirect_stdout
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowTaskEnqueued
from press.workflow_engine.doctype.press_workflow.press_workflow import enqueue_workflow
from press.workflow_engine.doctype.press_workflow_object.press_workflow_object import (
	PressWorkflowObject,
)
from press.workflow_engine.utils import calculate_duration, deserialize_value, serialize_and_store_value

if TYPE_CHECKING:
	from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder


class PressWorkflowTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		args: DF.Data | None
		args_type: DF.Literal["int", "float", "string", "tuple", "list", "dict", "object"]
		duration: DF.Duration | None
		end: DF.Datetime | None
		exception: DF.Link | None
		kwargs: DF.Data | None
		kwargs_type: DF.Data | None
		method_name: DF.Data
		method_title: DF.Data
		output: DF.Data | None
		output_type: DF.Literal["int", "float", "string", "tuple", "list", "dict", "object"]
		parent_task: DF.Link | None
		queue: DF.Data | None
		signature: DF.Data
		start: DF.Datetime | None
		status: DF.Literal["Queued", "Running", "Success", "Failure"]
		stdout: DF.LongText | None
		timeout: DF.Int
		traceback: DF.LongText | None
		workflow: DF.Link
	# end: auto-generated types

	def after_insert(self):
		enqueue_task(self.name)  # type: ignore

	def on_update(self):
		self.update_tracked_step_status()

	def update_tracked_step_status(self):
		if self.is_new():
			return

		if self.flags.in_insert:
			# Called from run_post_save_methods() after insert, where the in-memory status
			# is still the original "Queued" but the task may have already run synchronously
			return

		if not self.has_value_changed("status"):
			return

		new_status = {
			"Queued": "Pending",
			"Running": "Running",
			"Success": "Success",
			"Failure": "Failure",
		}.get(self.status, "Pending")

		# Primary lookup: find the step already linked to this task.
		step_name = frappe.db.get_value("Press Workflow Step", {"task": self.name}, "name")

		if not step_name:
			# Fallback: the step may not yet be linked (e.g. in synchronous test execution
			# where after_insert runs the task before run_task sets the step.task reference).
			step_name = frappe.db.get_value(
				"Press Workflow Step",
				{
					"parenttype": "Press Workflow",
					"parent": self.workflow,
					"step_method": self.method_name,
				},
				"name",
			)

		if step_name:
			frappe.db.set_value("Press Workflow Step", step_name, "status", new_status)

	def run(self):  # noqa: C901 - Best to keep workflow execution logic in one place
		assert self.name, "Task must be saved before it can be run"
		frappe.get_value(
			self.doctype, self.name, "name", for_update=(not frappe.flags.in_test)
		)  # Lock the document for update to prevent concurrent runs

		workflow_info = frappe.get_value(
			"Press Workflow",
			self.workflow,
			["name", "status", "linked_docname", "linked_doctype", "is_force_failure_requested"],
			as_dict=True,
		)

		reference_doc: WorkflowBuilder = frappe.get_doc(
			workflow_info.linked_doctype, workflow_info.linked_docname
		)  # type: ignore
		reference_doc.workflow_name = self.workflow
		reference_doc.flags.in_press_workflow_execution = True
		reference_doc.flags.current_press_workflow_task = self.name

		try:
			args = deserialize_value(self.args_type, self.args) if self.args else ()
			kwargs = deserialize_value(self.kwargs_type, self.kwargs) if self.kwargs else {}
		except Exception as e:
			self.exception = PressWorkflowObject.store(e, throw_on_error=False)
			self.status = "Failure"
			self.save()
			self._resume_workflow()
			return

		if not hasattr(reference_doc, self.method_name):
			self.exception = PressWorkflowObject.store(
				Exception(
					f"Method {self.method_name} not found in {reference_doc.doctype} {reference_doc.name}"
				)
			)
			self.status = "Failure"
			self.save()
			self._resume_workflow()
			return

		# Mark as Running immediately so the scheduler won't re-enqueue it
		# while this execution is in progress.
		if not self.start:
			self.start = now_datetime()

		self.status = "Running"
		self.save()
		if not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep

		output_value = None
		output_type = None
		exception = None
		exception_traceback = None
		status = "Running"
		buffer = io.StringIO()

		existing_task_signature = reference_doc.current_task_signature
		try:
			reference_doc.current_task_signature = self.signature

			if workflow_info.is_force_failure_requested:
				raise Exception("Workflow was forcefully failed based on user request.")

			with redirect_stdout(buffer):
				result = getattr(reference_doc, self.method_name)(*args, **kwargs)

			if result is not None:
				output_type, output_value = serialize_and_store_value(result)

			status = "Success"
		except PressWorkflowTaskEnqueued:
			# A nested task was enqueued while executing this task.
			# This is expected behaviour: exit without marking a terminal state
			# so this task will be retried later (same as the parent workflow).
			pass
		except Exception as e:
			exception = PressWorkflowObject.store(e, throw_on_error=False)
			status = "Failure"
			exception_traceback = frappe.get_traceback()

		finally:
			reference_doc.current_task_signature = existing_task_signature
			self.reload()

			if status in ["Success", "Failure"] and not self.end:
				self.end = now_datetime()

			if self.start and self.end and not self.duration:
				self.duration = calculate_duration(self.start, self.end)

			self.status = status
			self.output = output_value
			self.output_type = output_type
			self.exception = exception
			self.stdout = (self.stdout or "") + buffer.getvalue()
			self.traceback = exception_traceback or getattr(self, "traceback", None)

			if frappe.flags.in_test and self.stdout:
				print(self.stdout)

			self.save()

			if self.status in ["Success", "Failure"]:
				# On termination, resume the parent task or workflow.
				self._resume_workflow()
			else:
				# A nested task was enqueued; re-enqueue ourselves for retry.
				enqueue_task(self.name)

	def _resume_workflow(self):
		if self.parent_task:
			# This task was triggered by another task — re-enqueue the parent
			# so it can continue from where it was paused.
			enqueue_task(self.parent_task)
		else:
			# Top-level task -- resume the parent workflow.
			enqueue_workflow(self.workflow)


def on_doctype_update():
	frappe.db.add_index("Press Workflow Task", ["creation"])


def enqueue_task(task_name: str) -> None:
	if frappe.flags.in_test:
		from press.utils.test import foreground_enqueue_task

		foreground_enqueue_task(task_name)
		return
	queue = frappe.db.get_value("Press Workflow Task", task_name, "queue") or frappe.conf.get(
		"press_workflow_task_queue", "default"
	)
	timeout = frappe.db.get_value("Press Workflow Task", task_name, "timeout") or 300
	frappe.enqueue_doc(
		"Press Workflow Task",
		task_name,
		method="run",
		queue=queue,
		timeout=timeout,
		deduplicate=True,
		enqueue_after_commit=True,
		job_id=f"press_workflow_task||{task_name}||run",
	)


def retry_tasks():
	tasks = frappe.get_all(
		"Press Workflow Task",
		filters={"status": ("in", ["Queued", "Running"])},
		pluck="name",
		order_by="modified asc",
	)
	for task_name in tasks:
		try:
			enqueue_task(task_name)
		except Exception as e:
			frappe.log_error(
				"Error Processing task",
				message=str(e),
				reference_doctype="Press Workflow Task",
				reference_name=task_name,
			)
