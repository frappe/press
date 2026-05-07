# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import json
from functools import cached_property
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

	from press.press.doctype.press_job.jobs.archive_server import ArchiveServerJob
	from press.press.doctype.press_job.jobs.attach_volume import AttachVolumeJob
	from press.press.doctype.press_job.jobs.auto_scale_application_server import (
		AutoScaleApplicationServerJob,
	)
	from press.press.doctype.press_job.jobs.auto_scale_down_application_server import (
		AutoScaleDownApplicationServerJob,
	)
	from press.press.doctype.press_job.jobs.auto_scale_up_application_server import (
		AutoScaleUpApplicationServerJob,
	)
	from press.press.doctype.press_job.jobs.create_cluster_registry import CreateClusterRegistryJob
	from press.press.doctype.press_job.jobs.create_server import CreateServerJob
	from press.press.doctype.press_job.jobs.create_server_snapshot import CreateServerSnapshotJob
	from press.press.doctype.press_job.jobs.increase_disk_size import IncreaseDiskSizeJob
	from press.press.doctype.press_job.jobs.increase_swap import IncreaseSwapJob
	from press.press.doctype.press_job.jobs.prune_docker_system import PruneDockerSystemJob
	from press.press.doctype.press_job.jobs.prune_mirror_registry import PruneMirrorRegistryJob
	from press.press.doctype.press_job.jobs.remove_on_prem_failover import RemoveOnPremFailoverJob
	from press.press.doctype.press_job.jobs.reset_swap_on_server import ResetSwapOnServerJob
	from press.press.doctype.press_job.jobs.resize_server import ResizeServerJob
	from press.press.doctype.press_job.jobs.resume_services_after_snapshot import (
		ResumeServicesAfterSnapshotJob,
	)
	from press.press.doctype.press_job.jobs.setup_on_prem_failover import SetupOnPremFailoverJob
	from press.press.doctype.press_job.jobs.snapshot_disk import SnapshotDiskJob
	from press.press.doctype.press_job.jobs.stop_and_start_server import StopAndStartServerJob
	from press.press.doctype.press_job.jobs.trigger_build_server_cleanup import (
		TriggerBuildServerCleanupJob,
	)
	from press.press.doctype.press_job.jobs.upgrade_mariadb import UpgradeMariaDBJob
	from press.press.doctype.press_job.jobs.warn_disk import WarnDiskJob

	_JOBS_REGISTRY = {
		"Archive Server": ArchiveServerJob,
		"Attach Volume": AttachVolumeJob,
		"Auto Scale Application Server": AutoScaleApplicationServerJob,
		"Auto Scale Down Application Server": AutoScaleDownApplicationServerJob,
		"Auto Scale Up Application Server": AutoScaleUpApplicationServerJob,
		"Create Server": CreateServerJob,
		"Create Server Snapshot": CreateServerSnapshotJob,
		"Increase Disk Size": IncreaseDiskSizeJob,
		"Increase Swap": IncreaseSwapJob,
		"Prune Docker system": PruneDockerSystemJob,
		"Prune Mirror Registry": PruneMirrorRegistryJob,
		"Remove On-Prem Failover": RemoveOnPremFailoverJob,
		"Reset Swap": ResetSwapOnServerJob,
		"Resize Server": ResizeServerJob,
		"Resume Services After Snapshot": ResumeServicesAfterSnapshotJob,
		"Setup On-Prem Failover": SetupOnPremFailoverJob,
		"Snapshot Disk": SnapshotDiskJob,
		"Stop and Start Server": StopAndStartServerJob,
		"Trigger Build Server Cleanup": TriggerBuildServerCleanupJob,
		"Upgrade MariaDB": UpgradeMariaDBJob,
		"Warn disk at 80%": WarnDiskJob,
		"Create Cluster Registry": CreateClusterRegistryJob,
	}


class PressJob(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		arguments: DF.SmallText
		duration: DF.Duration | None
		end: DF.Datetime | None
		job_type: DF.Data
		name: DF.Int | None
		server: DF.DynamicLink | None
		server_type: DF.Link | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Skipped", "Success", "Failure"]
		virtual_machine: DF.Link | None
	# end: auto-generated types

	@cached_property
	def arguments_dict(self) -> "frappe._dict":
		return frappe._dict(json.loads(self.get("arguments") or "{}"))

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

	@property
	def steps(self) -> list[dict[str, str]]:
		try:
			workflow: PressWorkflow = frappe.get_last_doc("Press Workflow", {"linked_docname": self.name})
			tasks = frappe.get_all(
				"Press Workflow Task",
				filters={"workflow": workflow.name},
				fields=[
					"name",
					"method_title",
					"status",
					"stdout",
					"creation",
					"start",
					"end",
					"duration",
				],
			)
			# Convert to a dict with task name as key for easy lookup
			task_dict = {task.name: task for task in tasks}
			return [
				{
					"name": step.name,
					"step_name": step.step_title,  # backward compatibility
					"step_title": step.step_title,
					"status": step.status,
					"result": task_dict.get(step.task, {}).get("stdout", ""),
					"traceback": task_dict.get(step.task, {}).get("traceback", ""),
					"start": task_dict.get(step.task, {}).get("start"),
					"end": task_dict.get(step.task, {}).get("end"),
					"duration": task_dict.get(step.task, {}).get("duration"),
				}
				for step in workflow.steps
			]
		except frappe.DoesNotExistError:
			return []

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
		if self.status != "Pending":
			frappe.throw(
				"Only jobs with Pending status can be started.<br>Please wait and retry after some time."
			)

		if not hasattr(self, "execute"):
			raise NotImplementedError("Press Job implementation must have an execute method")
		self.start = now_datetime()
		self.status = "Running"
		self.save(ignore_permissions=True)
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

	@frappe.whitelist()
	def retry(self):
		if self.status != "Failure":
			frappe.throw("Only workflows in Failure state can be retried.")  # nosemgrep
			return

		self.status = "Pending"
		self.save()
		self.start_workflow()
		frappe.db.commit()  # nosemgrep
