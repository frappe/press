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
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.release_group.release_group import ReleaseGroup


BENCH_TRANSITION_STATES = ["Pending", "Installing", "Updating"]


class FailedBenchJobs(TypedDict):
	name: str
	bench: str


class BenchInfo(TypedDict):
	name: str
	status: str


class ReleasePipelineFailure(Exception):
	pass


class ReleasePipeline(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		release_group: DF.Link | None
		status: DF.Literal["Pending", "Running", "Partial Success", "Success", "Failure", "Retrying"]
		team: DF.Link

	# end: auto-generated types

	def update_pipeline_status(
		self,
		status: typing.Literal[
			"Pending",
			"Running",
			"Partial Success",
			"Success",
			"Failure",
			"Retrying",
		],
	):
		self.status = status
		self.save()

	@cached_property
	def release_group_doc(self) -> "ReleaseGroup":
		return frappe.get_doc("Release Group", self.release_group)

	@cached_property
	def workflow_name(self) -> str:
		return frappe.db.get_value(
			"Press Workflow", {"linked_doctype": "Release Pipeline", "linked_docname": self.name}, "name"
		)

	def get_task_name(self, func):
		"""Get task name for the given function"""
		return frappe.db.get_value(
			"Press Workflow Task", {"method_name": func.__name__, "workflow": self.workflow_name}, "name"
		)

	@task
	def validate_app_hashes(self, apps: list[dict[str, str]]):
		"""Validate App Hashes"""
		from press.api.bench import validate_app_hashes as app_hash_validation

		app_hash_validation(apps)

		self.update_pipeline_status("Running")  # Mark the pipeline as running!

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
			self.release_group, apps, sites, is_inplace_update=False, ignore_permissions_check=True
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

	def _get_required_build_count(self, deploy_candidate: str) -> int:
		"""Get the number of builds required for this deploy, as we can have arm & intel build for the same deploy candidate"""
		intel_build, arm_build = frappe.db.get_value(
			"Deploy Candidate", deploy_candidate, ["requires_intel_build", "requires_arm_build"]
		)

		return len([build for build in [intel_build, arm_build] if build])

	def _check_for_scheduled_build_retries(self, deploy_candidate_build: str):
		"""Check if there are any scheduled retries for this build"""
		deploy_candidate_build_doc: DeployCandidateBuild = frappe.get_doc(
			"Deploy Candidate Build", deploy_candidate_build
		)

		agent_job: AgentJob = frappe.get_doc(
			"Agent Job",
			{
				"reference_doctype": "Deploy Candidate Build",
				"reference_name": deploy_candidate_build,
				"job_type": "Run Remote Builder",
			},
		)

		if deploy_candidate_build_doc.should_build_retry(exc=None, job=agent_job):
			self.update_pipeline_status("Retrying")
			raise PressWorkflowTaskEnqueued(
				f"Build {deploy_candidate_build} has scheduled retries. Waiting for retries to complete.",
				self.workflow_name,
				self.get_task_name(self.monitor_pre_build_validation),
			)

	def _get_latest_retried_build(self, deploy_candidate_build: str) -> str:
		"""In case there are retries for the build, get the latest retried build to monitor."""
		deploy_candidate, retry_count = frappe.db.get_value(
			"Deploy Candidate Build", deploy_candidate_build, ["deploy_candidate", "retry_count"]
		)

		retried_build = frappe.db.get_value(
			"Deploy Candidate Build",
			{
				"group": self.release_group,
				"deploy_candidate": deploy_candidate,
				"retry_count": retry_count + 1,
			},
			"name",
		)

		return retried_build or deploy_candidate_build

	@task
	def monitor_pre_build_validation(self, deploy_candidate_build: str):
		"""Monitors the Deploy Candidate Build until the remote build job is created."""
		task_name = self.get_task_name(self.monitor_pre_build_validation)
		deploy_candidate_build_status = frappe.db.get_value(
			"Deploy Candidate Build", deploy_candidate_build, "status"
		)

		if deploy_candidate_build_status in ["Running", "Success"]:
			return  # We have enqueued the remote agent job

		if deploy_candidate_build_status == "Failure":
			raise ReleasePipelineFailure(
				f"Pre Build Validation failed for Deploy Candidate Build {deploy_candidate_build}. "
				"Please check the build logs for more details."
			)

		raise PressWorkflowTaskEnqueued(
			f"Waiting for remote build job to be enqueued for Deploy Candidate Build {deploy_candidate_build}",
			self.workflow_name,
			task_name,
		)

	@task
	def monitor_build_success(self, deploy_candidate_build: str):
		"""Monitor build till terminal state."""
		deploy_candidate_build = self._get_latest_retried_build(deploy_candidate_build)
		deploy_candidate_build_status = frappe.db.get_value(
			"Deploy Candidate Build", deploy_candidate_build, "status"
		)

		if deploy_candidate_build_status == "Success":
			return  # Remote Build succeeded can mark as success and proceed

		if deploy_candidate_build_status == "Failure":
			# This will raise and enqueue the function again in case there are scheduled retries for the build
			self._check_for_scheduled_build_retries(deploy_candidate_build)
			raise ReleasePipelineFailure(
				f"Remote build failed for Deploy Candidate Build {deploy_candidate_build}. Please check the build logs for more details."
			)

		raise PressWorkflowTaskEnqueued(
			f"Waiting for build to complete for Deploy Candidate Build {deploy_candidate_build}",
			self.workflow_name,
			self.get_task_name(self.monitor_build_success),
		)

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
		builds = [build for build in [intel_build, arm_build] if build]

		if not builds:
			raise ReleasePipelineFailure(f"No builds found for Deploy Candidate {candidate}.")

		# Account for previously created failed bench docs
		bench_info = frappe.db.get_all(
			"Bench", {"build": ("in", builds), "status": ("!=", "Archived")}, ["name", "status"]
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

	def _check_for_scheduled_bench_retries(self, failed_bench_deploys: list[FailedBenchJobs]):
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
			self.update_pipeline_status("Retrying")
			raise PressWorkflowTaskEnqueued(
				"Some bench deploys have failed but are scheduled for retry. Waiting for retries to complete.",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

	def _finalize_pipeline_status(
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
			return self.update_pipeline_status("Success")

		if num_failed > 0:
			# This will raise and enqueue function again in case of scheduled retries
			# In case there are no scheduled retries it will simply continue to evaluate the failure
			self._check_for_scheduled_bench_retries(failed_bench_deploys)

		# Case 2: Total Failure
		if num_failed == num_total:
			self.update_pipeline_status("Failure")
			raise ReleasePipelineFailure(
				f"All bench deploys failed for Build {deploy_candidate_build}. Check jobs for details."
			)

		# Case 3: Partial Success
		print(f"Some bench deploys failed for Build {deploy_candidate_build}. Check jobs for details.")
		return self.update_pipeline_status("Partial Success")

	def _get_secondary_build(self, deploy_candidate: str, primary_build: str) -> str | None:
		"""Finds a build for the same candidate but on a different platform."""
		primary_platform = frappe.db.get_value("Deploy Candidate Build", primary_build, "platform")

		return frappe.db.get_value(
			"Deploy Candidate Build",
			{
				"deploy_candidate": deploy_candidate,
				"name": ("!=", primary_build),
				"group": self.release_group,
				"platform": ("!=", primary_platform),
			},
			"name",
		)

	@task
	def monitor_bench_creation(self, deploy_candidate_build: str):
		"""Monitor new bench creation accounting for any failures and retries."""
		if self.status == "Retrying":
			self.update_pipeline_status(
				"Running"
			)  # Reset status to running when we start monitoring again after retry

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
		self._finalize_pipeline_status(failed_bench_deploys, bench_info, deploy_candidate_build)

	def run_pre_release_checks(self, apps: list[dict[str, str]]):
		"""Groups all early-exit validation logic."""
		self.validate_app_hashes(apps)  # This sets status to "Running"
		self.validate_server_storages()
		self.validate_auto_scales_on_servers()

	def prepare_deployment(self, apps, sites, run_will_fail_check) -> tuple[str, str]:
		"""Creates the candidate and returns the primary build name."""
		deploy_candidate = self.create_deploy_candidate(
			apps=apps,
			sites=sites,
			run_will_fail_check=run_will_fail_check,
			create_deploy=False,
		)
		primary_build = self.initiate_pre_build_validations(deploy_candidate)
		return deploy_candidate, primary_build

	def orchestrate_build_monitoring(self, deploy_candidate: str, primary_build: str):
		"""Monitors primary and, if necessary, secondary builds."""
		# Monitor Primary
		self.monitor_pre_build_validation(primary_build)
		self.monitor_build_success(primary_build)

		# Check for Secondary Architecture
		if self._get_required_build_count(deploy_candidate) == 2:
			secondary_build = self._get_secondary_build(deploy_candidate, primary_build)

			if not secondary_build:
				# Wait for sometime for the secondary build to be created in case of any delays in build scheduling
				raise PressWorkflowTaskEnqueued(
					f"Waiting for secondary build creation for {deploy_candidate}",
					self.workflow_name,
					self.get_task_name(self.monitor_build_success),
				)

			self.monitor_pre_build_validation(secondary_build)
			self.monitor_build_success(secondary_build)

	@flow
	def create_release(
		self,
		apps: list[dict[str, str]],
		sites: list[dict[str, Any]],
		run_will_fail_check: bool = False,
	):
		"""Orchestrates the release process from validation to bench creation with recursive monitoring and retry handling"""
		try:
			# 1. Validation Phase
			self.run_pre_release_checks(apps)

			# 2. Initialization Phase
			deploy_candidate, primary_build = self.prepare_deployment(apps, sites, run_will_fail_check)

			# 3. Monitoring Phase (Handles 1 or 2 builds)
			self.orchestrate_build_monitoring(deploy_candidate, primary_build)

			# 4. Finalization Phase
			self.monitor_bench_creation(primary_build)

		except ReleasePipelineFailure:
			self.update_pipeline_status("Failure")
