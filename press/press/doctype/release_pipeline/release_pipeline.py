# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import typing
from datetime import datetime, timedelta
from functools import cached_property
from typing import Any, TypedDict

import frappe
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from press.api.github import get_dependant_apps_with_versions
from press.exceptions import InsufficientSpaceOnServer, ReleasePipelineFailure
from press.press.doctype.app.app import (
	get_app_source_from_supported_versions,
	get_latest_release_of_app_from_source,
	parse_frappe_version,
)
from press.press.doctype.bench_update.bench_update import get_bench_update
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
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

KNOWN_PYTHON_VERSIONS = ["3.8", "3.9", "3.10", "3.11", "3.12", "3.13", "3.14"]


class FailedBenchJobs(TypedDict):
	name: str
	bench: str


class BenchInfo(TypedDict):
	name: str
	status: str


def _resolve_dependent_app(app: str, supported_frappe_version: set[str]) -> tuple[AppSource, AppRelease]:
	"""Resolve app source and latest release for a dependent app."""
	if not frappe.db.exists("App", app):
		raise ReleasePipelineFailure(
			f"Dependent app {app} does not exist in the system. "
			"Please add this app to your bench group first."
		)

	app_source = get_app_source_from_supported_versions(
		app=app,
		supported_versions=supported_frappe_version,
	)
	if not app_source:
		raise ReleasePipelineFailure(
			f"Unable to find an app source for dependent app {app} "
			f"with supported versions {supported_frappe_version}. "
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


def _resolve_python_version_conflicts_and_update_group(
	release_group_name: str, python_versions: dict[str, str | None]
) -> None:
	"""Resolve any python version conflicts and update the release group with the final python version requirements.
	Eg, python_versions - {"app1": "~3.10", "app2": ">=3.11", "app3": ">=3.10"}
	"""
	combined_spec = SpecifierSet()

	for app_name, spec_string in python_versions.items():
		if not spec_string:
			# App didn't specify any python version requirements.
			continue

		try:
			# Combine all the python versions
			current_app_spec = SpecifierSet(spec_string)
			combined_spec &= current_app_spec
		except InvalidSpecifier:
			raise ReleasePipelineFailure(
				f"Invalid Python version format for {app_name}: {spec_string}"
			) from None

	compatible_versions = [Version(v) for v in KNOWN_PYTHON_VERSIONS if Version(v) in combined_spec]

	if not compatible_versions:
		raise ReleasePipelineFailure(
			"Python version conflict detected between apps please resolve the python version conflict and retry"
		)

	highest_compatible_python_version = max(compatible_versions)
	release_group_doc: ReleaseGroup = frappe.get_doc("Release Group", release_group_name, for_update=True)

	for dependency in release_group_doc.dependencies:
		if dependency.dependency == "PYTHON_VERSION":
			dependency.version = str(highest_compatible_python_version)
			dependency.is_custom = True
			dependency.save(ignore_permissions=True)


class ReleasePipeline(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.release_pipeline_build.release_pipeline_build import ReleasePipelineBuild

		is_user_addressable_failure: DF.Check
		pipeline_builds: DF.Table[ReleasePipelineBuild]
		release_group: DF.Link | None
		status: DF.Literal["Pending", "Running", "Partial Success", "Success", "Failure", "Retrying"]
		team: DF.Link
		workflow: DF.Link | None
	# end: auto-generated types

	def send_failure_notification(self):
		workflow = frappe.get_doc("Press Workflow", self.workflow)
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
		# If the workflow doc touches this for any reason
		# Document native methods would raise a `TimeStampMismatch` error
		self.db_set("status", status)

		if status == "Failure":
			self.send_failure_notification()

	def add_build_to_pipeline(self, build: str):
		"""Attach a build to the pipeline if not present"""
		existing_builds = [pb.build for pb in self.pipeline_builds]

		if build not in existing_builds:
			self.append("pipeline_builds", {"build": build})
			self.save()

	@cached_property
	def release_group_doc(self) -> "ReleaseGroup":
		return frappe.get_doc("Release Group", self.release_group)

	@cached_property
	def current_workflow(self) -> str:
		return frappe.db.get_value(
			"Press Workflow", {"linked_doctype": "Release Pipeline", "linked_docname": self.name}, "name"
		)

	@staticmethod
	def _get_task_execution_queue() -> str:
		"""Determine the appropriate queue for task execution based on the release group."""
		return "default" if frappe.conf.developer_mode else "build"

	@task(queue=_get_task_execution_queue())
	def validate_app_hashes(self, apps: list[dict[str, str]]):
		"""Validate App Hashes"""
		from press.api.bench import validate_app_hashes as app_hash_validation

		app_hash_validation(apps)

		self.update_pipeline_status("Running")  # Mark the pipeline as running!

	@task(queue=_get_task_execution_queue())
	def validate_invalid_releases(self, apps: list[dict[str, str]]):
		"""Validate that none of the apps being deployed have invalid releases."""
		for app in apps:
			if not app.get("release"):
				continue

			# App release will always be present otherwise we won't be able to proceed.
			app_info = frappe.db.get_value(
				"App Release", app["release"], ["invalid_release", "invalidation_reason"], as_dict=True
			)
			if not app_info or not app_info["invalid_release"]:
				continue

			raise ReleasePipelineFailure(
				f"Invalid release found for app {app['app']} with hash {app['hash']}. Reason: {app_info['invalidation_reason']}"
			)

	@task(queue=_get_task_execution_queue())
	def validate_server_storages(self):
		"""Validate server storage for all servers in the release group."""
		self.release_group_doc.check_app_server_storage()

	@task(queue=_get_task_execution_queue())
	def validate_auto_scales_on_servers(self):
		"""Validate no server in release group is autoscaled."""
		self.release_group_doc.check_auto_scales()

	@task(queue=_get_task_execution_queue())
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
			self.release_group, apps, sites, is_inplace_update=False, ignore_permissions=True
		)
		return bench_update.deploy(
			run_will_fail_check=run_will_fail_check,
			validate_pre_candidate_checks=False,
			create_build=create_deploy,
			ignore_permissions=True,
		)

	@task(queue=_get_task_execution_queue())
	def initiate_pre_build_validations(self, deploy_candidate: str) -> str:
		"""Start the deploy candidate build process which will run the pre-build validations."""
		candidate: DeployCandidate = frappe.get_doc("Deploy Candidate", deploy_candidate)
		deploy_candidate_build = candidate.schedule_build_and_deploy(
			ignore_permissions=True,
		)
		return deploy_candidate_build["name"]

	def _get_required_build_count(self, deploy_candidate: str) -> int:
		"""Get the number of builds required for this deploy, as we can have arm & intel build for the same deploy candidate"""
		intel_build, arm_build = frappe.db.get_value(
			"Deploy Candidate", deploy_candidate, ["requires_intel_build", "requires_arm_build"]
		)

		return len([build for build in [intel_build, arm_build] if build])

	def _mark_if_user_failure(self, deploy_candidate_build: str):
		user_addressable_failure, manually_failed = frappe.db.get_value(
			"Deploy Candidate Build", deploy_candidate_build, ["user_addressable_failure", "manually_failed"]
		)

		if user_addressable_failure or manually_failed:
			self.is_user_addressable_failure = True
			self.save()

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
			self.defer_current_task(
				message=f"Build {deploy_candidate_build} has scheduled retries. Waiting for retries to complete."
			)

		self._mark_if_user_failure(deploy_candidate_build_doc.name)

	def _get_latest_retried_build(self, deploy_candidate_build: str) -> str:
		"""In case there are retries for the build, get the latest retried build with same platform to monitor."""
		deploy_info = frappe.db.get_value(
			"Deploy Candidate Build", deploy_candidate_build, ["deploy_candidate", "platform"]
		)

		if deploy_info is None:
			raise ReleasePipelineFailure(f"Deploy Candidate Build {deploy_candidate_build} not found.")

		deploy_candidate, platform = deploy_info

		# Get the latest build
		return frappe.db.get_value(
			"Deploy Candidate Build",
			{
				"group": self.release_group,
				"deploy_candidate": deploy_candidate,
				"platform": platform,
			},
			"name",
			order_by="creation desc",
		)

	@task(queue=_get_task_execution_queue())
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

		self.defer_current_task(
			message=f"Waiting for build to complete for Deploy Candidate Build {deploy_candidate_build}",
		)

	def _fail_bench_job_if_obsolete(self, pending_agent_jobs: list[dict[str, str | datetime]]):
		"""Fail the bench job if it's creation time is older than 10 mins"""
		for job in pending_agent_jobs:
			assert isinstance(job["creation"], datetime), "Expected 'creation' to be a datetime object"
			if (job["creation"] <= frappe.utils.now_datetime() - timedelta(minutes=10)) and (
				job["status"] == "Undelivered"
			):
				# In case of undelivered jobs we can directly mark them as failure
				# And mark the bench as broken since they were never picked up by agent
				frappe.db.set_value("Agent Job", job["name"], "status", "Failure")
				frappe.db.set_value("Bench", job["bench"], "status", "Broken")

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

		pending_agent_jobs = frappe.db.get_all(
			"Agent Job",
			{
				"job_type": ["in", ["New Bench", "Archive Bench"]],
				"status": ["in", ["Undelivered", "Pending"]],
				"bench": ["in", benches_from_builds],
			},
			["name", "bench", "status", "creation"],
		)
		self._fail_bench_job_if_obsolete(pending_agent_jobs)
		# Even if there are no retries scheduled, we want to wait for the current bench jobs to be completed
		# This is after the obsolete jobs are marked as failed and their benches are marked as broken, so we only wait for
		# valid jobs to be completed and not the obsolete ones.
		agent_job_active = frappe.db.exists(
			"Agent Job",
			{
				"job_type": ["in", ["New Bench", "Archive Bench"]],
				"status": ["in", ["Running", "Pending", "Undelivered"]],
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
		self,
		deploy_candidate: DeployCandidate,
		supported_frappe_version: str | None,
		dependent_apps: set[str],
	):
		"""Helper function to add the dependant apps to the release group and deploy candidate automatically.
		In case we don't find the app or the app source in press we need to raise, and ask users to add
		the app in the bench group first.
		"""
		if not supported_frappe_version or not dependent_apps:
			return

		release_group_doc: ReleaseGroup = frappe.get_doc("Release Group", self.release_group, for_update=True)
		release_group_apps = {app.app for app in release_group_doc.apps}

		try:
			parsed_supported_frappe_version = parse_frappe_version(
				version_string=supported_frappe_version,
				app_title="frappe",
				ease_versioning_constrains=False,
			)
		except frappe.ValidationError:
			return

		for app in dependent_apps:
			if app in release_group_apps:
				continue

			app_source, app_release = _resolve_dependent_app(
				app,
				parsed_supported_frappe_version,
			)
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
		deploy_candidate.save(ignore_permissions=True)
		release_group_doc.save(ignore_permissions=True)

	@task(queue=_get_task_execution_queue())
	def run_pre_release_checks(self, apps: list[dict[str, str]]):
		"""Groups all early-exit validation logic."""
		is_enabled = frappe.db.get_value("Release Group", self.release_group, "enabled")
		if not is_enabled:
			self.is_user_addressable_failure = True
			self.save()
			raise ReleasePipelineFailure("Release Group is disabled. Updates can not be initiated.")

		try:
			self.validate_app_hashes(apps)  # This sets status to "Running"
			# Let this be here for when we have a invalid release already this will ensure we
			# Don't start the deploy with a invalid release
			self.validate_invalid_releases(apps)
			self.validate_server_storages()
			self.validate_auto_scales_on_servers()
		except (frappe.ValidationError, InsufficientSpaceOnServer) as e:
			raise ReleasePipelineFailure(str(e)) from e

	@task(queue=_get_task_execution_queue())
	def add_implicit_app_dependencies(self, deploy_candidate: str):
		"""Add any implicit dependencies for the apps being deployed."""
		deploy_candidate_doc: DeployCandidate = frappe.get_doc(
			"Deploy Candidate", deploy_candidate, for_update=True
		)
		for app in deploy_candidate_doc.apps:
			dependant_app_versions = get_dependant_apps_with_versions(
				app_source=app.source, commit=app.hash, cache=True, raises=False
			)
			supported_frappe_version = dependant_app_versions["frappe_dependencies"].get("frappe")
			dependent_apps = dependant_app_versions["frappe_dependencies"].keys() - {"frappe"}

			# Here we don't care about the version of the dependent apps, since we
			# will just be fetching the app source that complies with the supported frappe version
			self._add_app_to_group_and_candidate(
				deploy_candidate_doc,
				supported_frappe_version=supported_frappe_version,
				dependent_apps=dependent_apps,
			)

	@task(queue=_get_task_execution_queue())
	def auto_update_bench_dependency_versions(self, deploy_candidate: str):
		"""Auto update the versions of the dependencies depending on app requirements.
		Currently only supports python version upgrades
		"""
		deploy_candidate_doc: DeployCandidate = frappe.get_doc(
			"Deploy Candidate", deploy_candidate, for_update=True
		)
		required_python_versions = {}

		for app in deploy_candidate_doc.apps:
			# Should use the cache from the previous task
			dependant_app_versions = get_dependant_apps_with_versions(
				app_source=app.source, commit=app.hash, cache=True, raises=False
			)
			required_python_versions[app.app] = dependant_app_versions["python_version"]

		_resolve_python_version_conflicts_and_update_group(
			self.release_group_doc.name, required_python_versions
		)

	@task(queue=_get_task_execution_queue())
	def prepare_deployment(self, apps, sites, run_will_fail_check) -> tuple[str, str]:
		"""Creates the candidate and returns the primary build name."""
		auto_upgrade_dependencies = frappe.db.get_single_value(
			"Press Settings",
			"auto_upgrade_dependencies",
		)

		try:
			deploy_candidate = self.create_deploy_candidate(
				apps=apps,
				sites=sites,
				run_will_fail_check=run_will_fail_check,
				create_deploy=False,
			)
			self.add_implicit_app_dependencies(deploy_candidate)

			if auto_upgrade_dependencies:
				self.auto_update_bench_dependency_versions(deploy_candidate)

			primary_build = self.initiate_pre_build_validations(deploy_candidate)

			return deploy_candidate, primary_build
		except frappe.ValidationError as e:
			raise ReleasePipelineFailure(f"Failed to prepare deployment: {e!s}") from e

	@task(queue=_get_task_execution_queue())
	def orchestrate_build_monitoring(self, deploy_candidate: str, primary_build: str):
		"""Monitors primary and, if necessary, secondary builds."""
		# Monitor Primary
		self.add_build_to_pipeline(primary_build)
		self.monitor_build_success(primary_build)

		# Check for Secondary Architecture
		if self._get_required_build_count(deploy_candidate) == 2:
			secondary_build = self._get_secondary_build(deploy_candidate, primary_build)

			if not secondary_build:
				# Wait for sometime for the secondary build to be created in case of any delays in build scheduling
				self.defer_current_task(
					message=f"Waiting for secondary build creation for Deploy Candidate {deploy_candidate}",
				)

			assert secondary_build, "Secondary build should be present for candidates requiring 2 builds"
			self.add_build_to_pipeline(secondary_build)
			self.monitor_build_success(secondary_build)

		if self.status == "Retrying":
			# If we were in retrying status, it means builds have succeeded after retries, we can move back to running status
			self.update_pipeline_status("Running")

	@task(queue=_get_task_execution_queue())
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
			self.defer_current_task(
				message=f"Waiting for bench creation to complete for Deploy Candidate Build(s) {builds}",
			)

		# Just another safety lock to ensure no early failures occur
		statues = frappe.db.get_all("Bench", {"build": ["in", builds]}, pluck="status")
		in_transition = [status for status in statues if status in BENCH_TRANSITION_STATES]

		if in_transition:
			self.defer_current_task(
				message=f"Benches are still in transition states for Deploy Candidate Build(s) {builds}.",
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

	@flow
	def create_release(
		self,
		apps: list[dict[str, str]],
		sites: list[dict[str, Any]],
		run_will_fail_check: bool = False,
	):
		"""Orchestrates the release process from validation to bench creation with recursive monitoring and retry handling"""
		if not self.workflow:
			self.workflow = self.current_workflow
			self.save()

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
			# Just in case, make sure that we mark the pipeline as failed and notify the frontend to stop listening for deploy updates
			self.update_pipeline_status("Failure")

	def on_workflow_failure(self, *args, **kwargs):
		self.update_pipeline_status("Failure")
