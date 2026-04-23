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
from press.workflow_engine.utils import calculate_duration

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

		args: DF.Link | None
		duration: DF.Duration | None
		end: DF.Datetime | None
		exception: DF.Link | None
		key_value_store: DF.Table[PressWorkflowKV]
		kwargs: DF.Link | None
		linked_docname: DF.DynamicLink
		linked_doctype: DF.Link
		main_method_name: DF.Data
		main_method_title: DF.Data
		output: DF.Link | None
		start: DF.Datetime | None
		status: DF.Literal["Queued", "Running", "Success", "Failure", "Fatal"]
		stdout: DF.LongText | None
		steps: DF.Table[PressWorkflowStep]
		traceback: DF.LongText | None
		workflow_traceback: DF.LongText | None
	# end: auto-generated types

	def after_insert(self):
		enqueue_workflow(self.name)  # type: ignore

	def run(self):  # noqa: C901 - best to keep it in one place
		if not self.linked_doctype or not self.linked_docname:
			frappe.throw("Cannot run flow without linked_doctype and linked_docname", frappe.ValidationError)
			return

		try:
			reference_doc: WorkflowBuilder = frappe.get_doc(self.linked_doctype, self.linked_docname)  # type: ignore
			reference_doc.workflow_name = self.name
			reference_doc.flags.in_press_workflow_execution = True

			args = PressWorkflowObject.get_object(self.args) if self.args else ()
			kwargs = PressWorkflowObject.get_object(self.kwargs) if self.kwargs else {}
		except Exception:
			self.status = "Fatal"
			self.traceback = frappe.get_traceback()
			self.save()
			return

		output = None
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
			with redirect_stdout(buffer):
				result = getattr(reference_doc, self.main_method_name)(*args, **kwargs)

			if result is not None:
				output = PressWorkflowObject.store(result)  # type: ignore
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
			self.output = output
			self.stdout = (self.stdout or "") + buffer.getvalue()

			if frappe.flags.in_test and self.stdout:
				print(self.stdout)

			self.exception = exception
			self.workflow_traceback = workflow_exception_traceback or self.workflow_traceback
			self.update_skipped_steps_status(save=False)
			self.save()

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
				return PressWorkflowObject.get_object(self.output)
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
