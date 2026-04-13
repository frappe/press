# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing
from functools import cached_property
from typing import Any, TypedDict

import frappe

from press.api.github import get_dependant_apps_with_versions
from press.exceptions import InsufficientSpaceOnServer, ReleasePipelineFailure
from press.press.doctype.app.app import (
	get_app_source_from_supported_versions,
	get_latest_release_of_app_from_source,
	parse_frappe_version,
)
from press.press.doctype.bench_update.bench_update import get_bench_update
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowTaskEnqueued
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.app_source.app_source import AppSource
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.release_group.release_group import ReleaseGroup
	from press.workflow_engine.doctype.press_workflow.press_workflow import PressWorkflow


BENCH_TRANSITION_STATES = ["Pending", "Installing", "Updating"]
# Keeping this here now, will eventually move all notifications logic here.
SKIP_NOTIFICATIONS_FOR = ["orchestrate_build_monitoring", "monitor_bench_creation"]


class FailedBenchJobs(TypedDict):
	name: str
	bench: str


class BenchInfo(TypedDict):
	name: str
	status: str


def _resolve_dependent_app(app: str, version: str) -> tuple[AppSource, AppRelease]:
	"""Resolve app source and latest release for a dependent app."""
	supported_versions = parse_frappe_version(
		version_string=version,
		app_title=app,
		ease_versioning_constrains=False,
	)
	if not supported_versions:
		raise ReleasePipelineFailure(
			f"Failed to parse supported versions for app {app} "
			f"with version string {version}. Cannot proceed with release."
		)

	if not frappe.db.exists("App", app):
		raise ReleasePipelineFailure(
			f"Dependent app {app} does not exist in the system. "
			"Please add this app to your bench group first."
		)

	app_source = get_app_source_from_supported_versions(
		app=app,
		supported_versions=supported_versions,
	)
	if not app_source:
		raise ReleasePipelineFailure(
			f"Unable to find an app source for dependent app {app} "
			f"with supported versions {supported_versions}. "
			"Please add this app to your bench group."
		)

	app_release = get_latest_release_of_app_from_source(app_source)
	if not app_release:
		raise ReleasePipelineFailure(
			f"Unable to find a release for dependent app {app} "
			f"from app source {app_source.name}. "
			"Please add a release for this app in your bench group."
		)

	return app_source, app_release


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
		deploy_candidate = frappe.db.get_value(
			"Deploy Candidate Build", deploy_candidate_build, "deploy_candidate"
		)

		# Get the latest **retried** build
		retried_build = frappe.db.get_value(
			"Deploy Candidate Build",
			{
				"group": self.release_group,
				"deploy_candidate": deploy_candidate,
				"name": ("!=", deploy_candidate_build),
			},
			"name",
			order_by="creation desc",
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

	def _is_active_bench_work_in_progress(self, builds: list[str]) -> bool:
		"""Checks the entire lifecycle (Queue + Agent Jobs) for active work."""
		queue_active = frappe.db.exists(
			"New Bench Queue",
			{"group": self.release_group, "status": "Queued"},
		)
		if queue_active:
			return True

		benches_from_builds = frappe.db.get_all("Bench", {"build": ["in", builds]}, pluck="name")
		if not benches_from_builds:
			# No benches created yet and nothing in queue? No work in progress.
			# Since after insert of bench creates agent job immediately.
			return False

		will_benches_be_retried = frappe.db.exists(
			"Agent Job",
			{
				"job_type": "Archive Bench",
				"bench": ("in", benches_from_builds),
				"request_data": (
					"like",
					'%"retry_new_bench": true%',  # Since retry is being passed here it will definitely lead to creation of new bench
				),  # Should not be too heavy since bench is indexed?
				"status": ["in", ["Undelivered", "Pending", "Running"]],
			},
		)

		if will_benches_be_retried:
			self.update_pipeline_status("Retrying")
			return True

		# Even if there are no retries scheduled, we want to wait for the current bench jobs to be completed
		agent_job_active = frappe.db.exists(
			"Agent Job",
			{
				"job_type": ["in", ["New Bench", "Archive Bench"]],
				"status": ["in", ["Undelivered", "Pending", "Running"]],
				"bench": ["in", benches_from_builds],
			},
		)

		return bool(agent_job_active)

	def _calculate_bench_doc_requirements(self, candidate: str, builds: list[str]) -> int:
		# This can have intel and arm server both will have different builds
		number_of_expected_bench_docs = len(self.release_group_doc.servers)
		# Total number of bench docs created regardless of the server platforms

		if not builds:
			raise ReleasePipelineFailure(f"No builds found for Deploy Candidate {candidate}.")

		return number_of_expected_bench_docs

	def _finalize_pipeline_status(self, builds: list, expected_count: int):
		"""Finalize the pipeline status based on the number of failed bench deploys vs expected bench deploys."""
		successful_deploys = frappe.db.count("Bench", {"build": ["in", builds], "status": "Active"})

		if successful_deploys == expected_count:
			return self.update_pipeline_status("Success")

		if successful_deploys == 0:
			self.update_pipeline_status("Failure")
			raise ReleasePipelineFailure(f"All {expected_count} bench deploy(s) failed.")

		# If some succeeded and others are permanently failed
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

	def _add_app_to_group_and_candidate(
		self, deploy_candidate: DeployCandidate, dependant_app_versions: dict[str, str]
	):
		"""Helper function to add the dependant apps to the release group and deploy candidate automatically.
		In case we don't find the app or the app source in press we need to raise, and ask users to add
		the app in the bench group first.
		"""
		release_group_doc = frappe.get_doc("Release Group", self.release_group, for_update=True)

		for app, version in dependant_app_versions.items():
			app_source, app_release = _resolve_dependent_app(app, version)
			deploy_candidate.append(
				"apps",
				{
					"app": app,
					"source": app_source.name,
					"release": app_release.name,
					"hash": app_release.hash,
				},
			)
			release_group_doc.append("apps", {"app": app, "source": app_source.name})

		# Final save
		deploy_candidate.save()
		release_group_doc.save()

	@task
	def add_implicit_app_dependencies(self, deploy_candidate: str):
		"""Add any implicit dependencies for the apps being deployed."""
		deploy_candidate_doc: DeployCandidate = frappe.get_doc(
			"Deploy Candidate", deploy_candidate, for_update=True
		)
		for app in deploy_candidate_doc.apps:
			dependant_app_versions = get_dependant_apps_with_versions(app_source=app.source, commit=app.hash)
			self._add_app_to_group_and_candidate(
				deploy_candidate_doc, dependant_app_versions=dependant_app_versions
			)

	@task
	def run_pre_release_checks(self, apps: list[dict[str, str]]):
		"""Groups all early-exit validation logic."""
		try:
			self.validate_app_hashes(apps)  # This sets status to "Running"
			self.validate_server_storages()
			self.validate_auto_scales_on_servers()
		except (frappe.ValidationError, InsufficientSpaceOnServer) as e:
			raise ReleasePipelineFailure(str(e)) from e

	@task
	def prepare_deployment(self, apps, sites, run_will_fail_check) -> tuple[str, str]:
		"""Creates the candidate and returns the primary build name."""
		try:
			deploy_candidate = self.create_deploy_candidate(
				apps=apps,
				sites=sites,
				run_will_fail_check=run_will_fail_check,
				create_deploy=False,
			)
			self.add_implicit_app_dependencies(deploy_candidate)
			primary_build = self.initiate_pre_build_validations(deploy_candidate)
			return deploy_candidate, primary_build
		except frappe.ValidationError as e:
			raise ReleasePipelineFailure(f"Failed to prepare deployment: {e!s}") from e

	@task
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

		if self.status == "Retrying":
			# If we were in retrying status, it means builds have succeeded after retries, we can move back to running status
			self.update_pipeline_status("Running")

	@task
	def monitor_bench_creation(self, deploy_candidate_build: str):
		"""Monitor new bench creation accounting for any failures and retries."""
		candidate = frappe.db.get_value("Deploy Candidate Build", deploy_candidate_build, "deploy_candidate")
		intel_build, arm_build = frappe.db.get_value(
			"Deploy Candidate", candidate, ["intel_build", "arm_build"]
		)
		builds = [b for b in [intel_build, arm_build] if b]
		expected = self._calculate_bench_doc_requirements(candidate=candidate, builds=builds)

		# This should take care of the retries as well.
		if self._is_active_bench_work_in_progress(builds):
			raise PressWorkflowTaskEnqueued(
				"Benches in progress, Waiting...",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

		# Just another safety lock to ensure no early failures occur
		statues = frappe.db.get_all("Bench", {"build": ["in", builds]}, pluck="status")
		in_transition = [status for status in statues if status in BENCH_TRANSITION_STATES]

		if in_transition:
			raise PressWorkflowTaskEnqueued(
				"Benches are in transition states...",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

		self._finalize_pipeline_status(builds=builds, expected_count=expected)

	def get_failure_summary(self, workflow: PressWorkflow) -> str | None:
		"""The first failure gets fails everything"""
		point_of_failure = [step.task for step in workflow.steps if step.status == "Failure"]

		if not point_of_failure:
			return None

		point_of_failure = point_of_failure[0]
		workflow_object_name, method_name = frappe.db.get_value(
			"Press Workflow Task", point_of_failure, ["exception", "method_name"]
		)

		if method_name in SKIP_NOTIFICATIONS_FOR:
			# Notifications for build failures are handled separately in the deploy notifications
			return None

		return frappe.db.get_value("Press Workflow Object", workflow_object_name, "summary")

	def on_update(self):
		"""A few steps have their notifications handled seperately in (ref deploy_notifications.py) skipping them"""
		if not self.has_value_changed("status"):
			return

		if self.status != "Failure":
			return

		workflow = frappe.get_doc("Press Workflow", self.workflow_name)
		failure_summary = self.get_failure_summary(workflow)

		if not failure_summary:
			return  # No failed tasks found, no need to create a notification

		frappe.get_doc(
			{
				"doctype": "Press Notification",
				"title": "Update Failure",
				"type": "Bench Deploy",
				"is_actionable": False,
				"class": "Error",
				"team": self.team,
				"document_type": "Release Pipeline",
				"document_name": self.name,
				"message": failure_summary,
			}
		).insert()

		frappe.publish_realtime(
			"press_notification", doctype="Press Notification", message={"team": self.team}
		)

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

		# Just for sanity if we missed something
		if self.status == "Failure":
			self.update_pipeline_status("Failure")
