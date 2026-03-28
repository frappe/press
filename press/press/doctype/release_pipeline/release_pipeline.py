# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
import typing
from functools import cached_property
from typing import Any, TypedDict

import frappe

from press.press.doctype.bench_update.bench_update import get_bench_update
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowTaskEnqueued
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if typing.TYPE_CHECKING:
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.release_group.release_group import ReleaseGroup


AGENT_JOB_TRANSITION_STATES = ["Undelivered", "Pending", "Running"]
BENCH_TRANSITION_STATES = ["Pending", "Installing", "Updating"]


class FailedBenchJobs(TypedDict):
	name: str
	bench: str


class BenchInfo(TypedDict):
	name: str
	status: str


class ReleasePipeline(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		release_group: DF.Link | None
		status: DF.Literal["Pending", "Running", "Partial Success", "Success", "Failure", "Retrying"]
		team: DF.Link

	def update_release_status(self, status: str):
		frappe.db.set_value("Release Step", self.name, "status", status)

	@cached_property
	def release_group_doc(self) -> "ReleaseGroup":
		return frappe.get_doc("Release Group", self.release_group)

	@cached_property
	def workflow_name(self) -> str:
		return frappe.db.get_value(
			"Press Workflow", {"linked_doctype": "Release Step", "linked_docname": self.name}, "name"
		)

	def get_task_name(self, func):
		"""Get task name for the given function"""
		return frappe.db.get_value(
			"Press Workflow Task", {"method_name": func.__name__, "workflow": self.workflow_name}, "name"
		)

	@task
	def validate_app_hashes(self, apps: list[dict[str, str]]):
		"""Validate App Hashes"""
		from press.api.bench import validate_app_hashes

		validate_app_hashes(apps)

	@task
	def validate_server_storages(self):
		"""Validate server storage for all servers in the release group."""
		self.release_group_doc.check_app_server_storage()

	@task
	def validate_auto_scales_on_servers(self):
		"""Validate no server in release group is autoscaled."""
		self.release_group_doc.check_auto_scales()

	@task
	def create_deploy_candidate(
		self,
		apps: list[dict[str, str]],
		sites: list[dict[str, Any]],
		run_will_fail_check: bool = False,
		create_deploy: bool = False,
	) -> str:
		"""Create a Deploy Candidate for the release group."""
		assert isinstance(self.release_group, str)
		bench_update: BenchUpdate = get_bench_update(
			self.release_group,
			apps,
			sites,
			is_inplace_update=False,
		)
		return bench_update.deploy(
			run_will_fail_check=run_will_fail_check,
			validate_pre_candidate_checks=False,
			create_build=create_deploy,
		)

	@task
	def initiate_pre_build_validations(self, deploy_candidate: str) -> str:
		"""Start the deploy candidate build process which will run the pre-build validations."""
		candidate: DeployCandidate = frappe.get_doc("Deploy Candidate", deploy_candidate)
		deploy_candidate_build = candidate.schedule_build_and_deploy()
		return deploy_candidate_build["name"]

	@task
	def start_and_monitor_pre_build_validation(self, deploy_candidate_build: str):
		"""Monitors the Deploy Candidate Build until the remote build job is created."""
		task_name = self.get_task_name(self.start_and_monitor_pre_build_validation)
		status = frappe.db.get_value("Deploy Candidate Build", deploy_candidate_build, "status")

		if status in ["Pending", "Preparing"]:
			raise PressWorkflowTaskEnqueued(
				f"Waiting for remote build job to be enqueued for Deploy Candidate Build {deploy_candidate_build}",
				self.workflow_name,
				task_name,
			)

		if status == "Failure":
			raise Exception(
				f"Pre Build Validation failed for Deploy Candidate Build {deploy_candidate_build}. Please check the build logs for more details."
			)

		if status == "Running":
			return  # We have enqueued the remote agent job

	@task
	def monitor_remote_build_job(self, deploy_candidate_build: str):
		"""Monitor the remote build agent job until terminal state is reached."""
		remote_builder_status = frappe.db.get_value(
			"Agent Job",
			{
				"job_type": "Run Remote Builder",
				"reference_doctype": "Deploy Candidate Build",
				"reference_name": deploy_candidate_build,
			},
			"status",
		)

		if remote_builder_status in AGENT_JOB_TRANSITION_STATES:
			raise PressWorkflowTaskEnqueued(
				f"Waiting for remote builder job to complete for Deploy Candidate Build {deploy_candidate_build}",
				self.workflow_name,
				self.get_task_name(self.monitor_remote_build_job),
			)

		if remote_builder_status == "Failure":
			raise Exception(
				f"Remote build failed for Deploy Candidate Build {deploy_candidate_build}. Please check the build logs for more details."
			)

		if remote_builder_status == "Success":
			return  # Remote Build succeeded can mark as success and proceed

	def _calculate_bench_doc_requirements(
		self, deploy_candidate_build: str
	) -> tuple[int, int, list[BenchInfo]]:
		candidate = frappe.db.get_value("Deploy Candidate Build", deploy_candidate_build, "deploy_candidate")
		intel_build, arm_build = frappe.db.get_value(
			"Deploy Candidate", candidate, ["intel_build", "arm_build"]
		)
		# This can have intel and arm server both will have different builds
		number_of_expected_bench_docs = len(self.release_group_doc.servers)
		# Total number of bench docs created regardless of the server platforms
		bench_info = frappe.db.get_all(
			"Bench", {"build": ("in", [intel_build, arm_build])}, ["name", "status"]
		)
		created_bench_docs = len(bench_info)
		return number_of_expected_bench_docs, created_bench_docs, bench_info

	def _get_stray_bench_creation_failures(self, bench_info: list[BenchInfo]) -> list[FailedBenchJobs]:
		# This is to catch any bench creation failures that might have happened
		return frappe.get_all(
			"Agent Job",
			{
				"job_type": "New Bench",
				"bench": ("in", [info["name"] for info in bench_info]),
				"status": "Failure",
			},
			["name", "bench"],
		)

	def _check_for_scheduled_retries(self, failed_bench_deploys: list[FailedBenchJobs]):
		"""Raise in case any of the failed agent jobs have retires in the pipeline"""
		if not failed_bench_deploys:
			return

		will_benches_be_retried = frappe.db.exists(
			"Agent Job",
			{
				"job_type": "Archive Bench",
				"bench": ("in", [deploy["bench"] for deploy in failed_bench_deploys]),
				"request_data": (
					"like",
					'%"retry_new_bench": true%',
				),  # Should not be too heavy since bench is indexed?
			},
		)

		if will_benches_be_retried:
			self.update_release_status("Retrying")
			raise PressWorkflowTaskEnqueued(
				"Some bench deploys have failed but are scheduled for retry. Waiting for retries to complete.",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

	def _finalize_bench_status(
		self,
		failed_bench_deploys: list[FailedBenchJobs],
		bench_info: list[BenchInfo],
		deploy_candidate_build: str,
	):
		"""Evaluates failures and updates the release status accordingly."""
		num_failed = len(failed_bench_deploys)
		num_total = len(bench_info)

		# Case 1: Pure Success
		if num_failed == 0:
			return self.update_release_status("Success")

		# Case 2: Total Failure
		if num_failed == num_total:
			self.check_for_scheduled_retries(failed_bench_deploys)
			self.update_release_status("Failure")
			raise Exception(
				f"All bench deploys failed for Build {deploy_candidate_build}. Check jobs for details."
			)

		# Case 3: Partial Success
		print(f"Some bench deploys failed for Build {deploy_candidate_build}. Check jobs for details.")
		return self.update_release_status("Partial Success")

	@task
	def monitor_bench_creation(self, deploy_candidate_build: str):
		"""Monitor the new bench agent jobs created for this deploy candidate build"""

		number_of_expected_bench_docs, created_bench_docs, bench_info = (
			self._calculate_bench_doc_requirements(deploy_candidate_build)
		)

		# 1. Ensure docs exist
		if created_bench_docs != number_of_expected_bench_docs:
			raise PressWorkflowTaskEnqueued(
				f"Waiting for bench docs to be created for {deploy_candidate_build}",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

		# 2. Ensure jobs are out of transition states
		if any(info["status"] in BENCH_TRANSITION_STATES for info in bench_info):
			raise PressWorkflowTaskEnqueued(
				f"Waiting for bench jobs to complete for {deploy_candidate_build}",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

		# 3. Evaluate and finalize the outcome
		failed_bench_deploys = self._get_stray_bench_creation_failures(bench_info)
		self._finalize_bench_status(failed_bench_deploys, bench_info, deploy_candidate_build)

	@flow
	def create_release(
		self,
		apps: list[dict[str, str]],
		sites: list[dict[str, Any]],
		run_will_fail_check: bool = False,
	):
		"""Create a release for the release group."""
		self.update_release_status("Running")
		self.validate_app_hashes(apps)
		self.validate_server_storages()
		self.validate_auto_scales_on_servers()
		deploy_candidate = self.create_deploy_candidate(
			apps=apps,
			sites=sites,
			run_will_fail_check=run_will_fail_check,
			create_deploy=False,
		)
		deploy_candidate_build = self.initiate_pre_build_validations(deploy_candidate)
		self.start_and_monitor_pre_build_validation(deploy_candidate_build)
		self.monitor_remote_build_job(deploy_candidate_build)
		self.monitor_bench_creation(deploy_candidate_build)
