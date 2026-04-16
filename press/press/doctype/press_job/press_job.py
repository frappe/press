from __future__ import annotations

# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from typing import TYPE_CHECKING

import frappe
from frappe.utils import now_datetime

from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if TYPE_CHECKING:
	from press.press.doctype.database_server.database_server import DatabaseServer
	from press.press.doctype.server.server import Server
	from press.press.doctype.virtual_machine.virtual_machine import VirtualMachine
	from press.workflow_engine.doctype.press_workflow.press_workflow import PressWorkflow

_JOBS_REGISTRY: dict[str, type] = {}


def _init_jobs_registry() -> None:
	global _JOBS_REGISTRY
	if _JOBS_REGISTRY:
		return

	from press.press.doctype.press_job.jobs.reset_swap_on_server import ResetSwapOnServerJob

	_JOBS_REGISTRY = {
		"Reset Swap": ResetSwapOnServerJob,
	}


class PressJob(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		duration: DF.Duration | None
		end: DF.Datetime | None
		job_type: DF.Link
		name: DF.Int | None
		server: DF.DynamicLink | None
		server_type: DF.Link | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Skipped", "Success", "Failure"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

	@property
	def server_doc(self) -> "Server | DatabaseServer":
		if hasattr(self, "_server_doc") and self._server_doc:  # type: ignore
			return self._server_doc  # type: ignore
		self._server_doc = frappe.get_doc(self.server_type, self.server)
		return self._server_doc

	@property
	def virtual_machine_doc(self) -> VirtualMachine | None:
		if not self.virtual_machine:
			return None

		if hasattr(self, "_virtual_machine_doc") and self._virtual_machine_doc:  # type: ignore
			return self._virtual_machine_doc  # type: ignore
		self._virtual_machine_doc = frappe.get_doc("Virtual Machine", self.virtual_machine)
		return self._virtual_machine_doc  # type: ignore

	def before_insert(self):
		frappe.db.get_value(self.server_type, self.server, "status", for_update=True)
		if existing_jobs := frappe.db.get_all(
			self.doctype,
			{
				"status": ("in", ["Pending", "Running"]),
				"server_type": self.server_type,
				"server": self.server,
			},
			["job_type", "status"],
		):
			frappe.throw(
				f"A {existing_jobs[0].job_type} job is already {existing_jobs[0].status}. Please wait for the same."
			)

	def after_insert(self):
		self.start_workflow()

	def on_update(self):
		if self.has_value_changed("status"):
			save = False
			if self.status == "Running" and not self.start:
				self.start = now_datetime()
				save = True

			if self.status in ["Success", "Failure"]:
				if not self.start:
					self.start = now_datetime()
				if not self.end:
					self.end = now_datetime()
				save = True

			if save:
				self.save()

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.workflow_name = self.job_type
		_init_jobs_registry()
		if self.job_type in _JOBS_REGISTRY:
			self.__class__ = _JOBS_REGISTRY[self.job_type]

	def start_workflow(self) -> str:
		if not hasattr(self, "execute"):
			raise NotImplementedError("Press Job implementation must have an execute method")
		return self.execute.run_as_workflow()

	def on_workflow_success(self, workflow: "PressWorkflow"):
		self.status = "Success"
		self.save()

		if hasattr(self, "on_press_job_success"):
			self.on_press_job_success(workflow)

	def on_workflow_failure(self, workflow: "PressWorkflow"):
		self.status = "Failure"
		self.save()

		if hasattr(self, "on_press_job_failure"):
			self.on_press_job_failure(workflow)
