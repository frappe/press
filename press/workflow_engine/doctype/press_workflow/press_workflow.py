# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import io
from contextlib import redirect_stdout
from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from press.workflow_engine.doctype.press_workflow.exceptions import (
	PressWorkflowFailedError,
	PressWorkflowFatalError,
	PressWorkflowRunningError,
	PressWorkflowTaskEnqueued,
)
from press.workflow_engine.doctype.press_workflow_object.press_workflow_object import (
	PressWorkflowObject,
)
from press.workflow_engine.utils import (
	calculate_duration,
	deserialize_value,
	serialize_and_store_value,
)

if TYPE_CHECKING:
	from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder
	from press.workflow_engine.doctype.press_workflow_step.press_workflow_step import (
		PressWorkflowStep,
	)


class PressWorkflow(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.workflow_engine.doctype.press_workflow_kv.press_workflow_kv import PressWorkflowKV
		from press.workflow_engine.doctype.press_workflow_step.press_workflow_step import PressWorkflowStep

		args: DF.Data | None
		args_type: DF.Literal["int", "float", "string", "tuple", "list", "dict", "object"]
		callback_next_retry_at: DF.Datetime | None
		callback_status: DF.Literal["Pending", "Success", "Failure", "Fatal"]
		callback_traceback: DF.LongText | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		exception: DF.Link | None
		is_force_failure_requested: DF.Check
		key_value_store: DF.Table[PressWorkflowKV]
		kwargs: DF.Data | None
		kwargs_type: DF.Literal["int", "float", "string", "tuple", "list", "dict", "object"]
		linked_docname: DF.DynamicLink
		linked_doctype: DF.Link
		main_method_name: DF.Data
		main_method_title: DF.Data
		max_no_of_callback_attempts: DF.Int
		no_of_callback_attempts: DF.Int
		output: DF.Data | None
		output_type: DF.Literal[None]
		start: DF.Datetime | None
		status: DF.Literal["Queued", "Running", "Success", "Failure", "Fatal"]
		stdout: DF.LongText | None
		steps: DF.Table[PressWorkflowStep]
		traceback: DF.LongText | None
		workflow_traceback: DF.LongText | None
	# end: auto-generated types

	def before_save(self):
		if self.linked_docname:
			self.linked_docname = str(self.linked_docname)

	def after_insert(self):
		enqueue_workflow(self.name)  # type: ignore

	def on_trash(self):
		frappe.db.delete("Press Workflow Task", {"workflow": self.name})

	@frappe.whitelist()
	def force_fail(self):
		if self.status in ["Success", "Failure", "Fatal"]:
			frappe.throw("Cannot force fail a workflow that has already completed.")  # nosemgrep
			return

		frappe.db.set_value(self.doctype, self.name, "is_force_failure_requested", True)

	def run(self):  # noqa: C901 - best to keep it in one place
		if not self.linked_doctype or not self.linked_docname:
			frappe.throw("Cannot run flow without linked_doctype and linked_docname", frappe.ValidationError)
			return

		try:
			reference_doc: WorkflowBuilder = frappe.get_doc(self.linked_doctype, self.linked_docname)  # type: ignore
			reference_doc.workflow_name = self.name
			reference_doc.flags.in_press_workflow_execution = True

			args = deserialize_value(self.args_type, self.args) or ()
			kwargs = deserialize_value(self.kwargs_type, self.kwargs) or {}
		except Exception:
			self.status = "Fatal"
			self.traceback = frappe.get_traceback()
			self.save()
			return

		output_value = None
		output_type = None
		exception = None
		workflow_exception_traceback = None
		status = "Running"
		buffer = io.StringIO()
		start = now_datetime()

		# Mark as Running immediately so the scheduler won't re-enqueue it
		# while this execution is in progress.
		self.status = "Running"
		if not self.start:
			self.start = start
		self.save()

		if not frappe.flags.in_test:
			frappe.db.commit()  # nosemgrep

		try:
			if self.is_force_failure_requested:
				raise Exception("Workflow was forcefully failed based on user request.")

			with redirect_stdout(buffer):
				result = getattr(reference_doc, self.main_method_name)(*args, **kwargs)

			if result is not None:
				output_type, output_value = serialize_and_store_value(result)
			status = "Success"
		except PressWorkflowTaskEnqueued:
			# This is expected when a task is enqueued.
			# The workflow will be resumed when the task is executed.
			pass
		except Exception as e:
			exception = PressWorkflowObject.store(e, throw_on_error=False)
			status = "Failure"
			workflow_exception_traceback = frappe.get_traceback()
		finally:
			self.reload()

			if not self.start:
				self.start = start

			if status in ["Success", "Failure"] and not self.end:
				self.end = now_datetime()

			if self.start and self.end and not self.duration:
				self.duration = calculate_duration(self.start, self.end)

			self.status = status
			self.output = output_value
			self.output_type = output_type
			self.stdout = (self.stdout or "") + buffer.getvalue()

			if frappe.flags.in_test and self.stdout:
				print(self.stdout)

			self.exception = exception
			self.workflow_traceback = workflow_exception_traceback or getattr(
				self, "workflow_traceback", None
			)
			self.update_skipped_steps_status(save=False)
			self.save()

		if frappe.flags.in_test:
			self.execute_callback()
		else:
			self.execute_callback_in_background()

	def execute_callback_in_background(self):
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			method="execute_callback",
			queue="default",
			timeout=300,
			deduplicate=True,
			enqueue_after_commit=True,
			job_id=f"press_workflow||{self.name}||execute_callback",
		)

	def execute_callback(self):
		"""
		If the workflow reached it's termination state, execute callback
		- on_workflow_success(doc:PressWorkflow) if status is Success
		- on_workflow_failure(doc:PressWorkflow) if status is Failure
		"""

		if self.status not in ["Success", "Failure"]:
			return

		if not frappe.db.exists(self.linked_doctype, self.linked_docname):
			return

		reference_doc: WorkflowBuilder = frappe.get_doc(self.linked_doctype, self.linked_docname)  # type: ignore
		callback_method = {
			"Success": "on_workflow_success",
			"Failure": "on_workflow_failure",
		}[self.status]

		if not hasattr(reference_doc, callback_method):
			self.callback_status = "Success"
			self.save()
			return

		try:
			getattr(reference_doc, callback_method)(self)
			self.callback_status = "Success"
			self.save()
		except Exception as e:
			frappe.log_error(
				f"Error executing workflow callback {callback_method}",
				message=str(e),
				reference_doctype=self.linked_doctype,
				reference_name=self.linked_docname,
			)

			self.no_of_callback_attempts += 1
			if self.no_of_callback_attempts >= self.max_no_of_callback_attempts:
				self.callback_status = "Fatal"
				self.callback_traceback = frappe.get_traceback()
			else:
				self.callback_status = "Failure"
				self.callback_next_retry_at = frappe.utils.add_to_date(
					minutes=2**self.no_of_callback_attempts
				)

			self.save()

			if self.callback_status == "Fatal":
				frappe.log_error(
					f"Workflow {self.name} has reached max callback retry attempts and is marked as Fatal",
					reference_doctype="Press Workflow",
					reference_name=self.name,
				)

	def update_skipped_steps_status(self, save: bool = True):  # noqa: C901 - best to keep it in one place
		is_updated = False

		if self.status in ["Success", "Failure"]:
			# Mark steps as skipped if they don't have a task associated
			for step in self.steps:
				if step.task:
					continue
				step.status = "Skipped"
				is_updated = True
		else:
			# Mark steps as skipped if the next step has a task associated
			previous_steps_with_no_task: list[PressWorkflowStep] = []
			for step in self.steps:
				if step.task:
					if previous_steps_with_no_task:
						for s in previous_steps_with_no_task:
							s.status = "Skipped"
						is_updated = True
						previous_steps_with_no_task = []
				else:
					previous_steps_with_no_task.append(step)

		if is_updated and save:
			self.save()

	def get_result(self):
		if self.status in ["Queued", "Running"]:
			raise PressWorkflowRunningError(
				f"Workflow {self.name} is currently {'running' if self.status == 'Running' else 'queued'}"
			)

		if self.status == "Success":
			if self.output:
				return deserialize_value(self.output_type, self.output)
			return None

		if self.status == "Failure":
			if self.exception:
				exc = PressWorkflowObject.get_object(self.exception)
				if isinstance(exc, Exception):
					raise exc
				raise PressWorkflowFailedError(f"Workflow failed with exception: {exc}")
			raise PressWorkflowFailedError("Workflow failed but no exception was recorded.")

		if self.status == "Fatal":
			raise PressWorkflowFatalError("Workflow encountered a fatal error.", traceback=self.traceback)

		return None


def enqueue_workflow(workflow_name: str) -> None:
	if frappe.flags.in_test:
		from press.utils.test import foreground_enqueue_workflow

		foreground_enqueue_workflow(workflow_name)
		return

	frappe.enqueue_doc(
		"Press Workflow",
		workflow_name,
		method="run",
		queue=frappe.conf.get("press_workflow_queue", "short"),
		timeout=3600,
		deduplicate=True,
		enqueue_after_commit=True,
		job_id=f"press_workflow||{workflow_name}||run",
	)


def retry_workflows():
	workflows = frappe.get_all(
		"Press Workflow",
		filters={"status": ("in", ["Queued", "Running"])},
		pluck="name",
		order_by="modified asc",
	)
	for workflow_name in workflows:
		try:
			enqueue_workflow(workflow_name)
		except Exception as e:
			frappe.log_error(
				"Error Processing workflow",
				message=str(e),
				reference_doctype="Press Workflow",
				reference_name=workflow_name,
			)


def retry_workflow_callbacks():
	workflows = frappe.get_all(
		"Press Workflow",
		filters={
			"callback_status": "Failure",
			"callback_next_retry_at": ("<=", now_datetime()),
		},
		pluck="name",
		order_by="modified asc",
	)

	# Include workflows with no callback_next_retry_at_set
	# and in Pending or Failure state
	workflows += frappe.get_all(
		"Press Workflow",
		filters={
			"callback_status": ("in", ["Pending", "Failure"]),
			"callback_next_retry_at": None,
		},
		pluck="name",
		order_by="modified asc",
	)

	for workflow_name in workflows:
		try:
			workflow: PressWorkflow = frappe.get_doc("Press Workflow", workflow_name)
			workflow.execute_callback_in_background()
		except Exception as e:
			frappe.log_error(
				"Error retrying workflow callback",
				message=str(e),
				reference_doctype="Press Workflow",
				reference_name=workflow_name,
			)
