# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
import typing
from functools import cached_property
from typing import Any

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


class ReleaseStep(WorkflowBuilder):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		release_group: DF.Link | None
		team: DF.Link

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

	@task
	def monitor_bench_creation(self, deploy_candidate_build: str):
		"""Monitor the new bench agent jobs created for this deploy candidate build"""
		# In this we need to smartly wait for all the agent jobs for the bench to be created
		number_of_expected_jobs = len(self.release_group_doc.servers)  # One bench server for on build
		created_bench_docs = frappe.db.count("Bench", {"build": deploy_candidate_build})

		# We haven't created all the bench docs yet for this build
		if created_bench_docs != number_of_expected_jobs:
			raise PressWorkflowTaskEnqueued(
				f"Waiting for bench docs to be created for Deploy Candidate Build {deploy_candidate_build}",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

		bench_statuses = frappe.get_all("Bench", {"build": deploy_candidate_build}, pluck="status")
		if any(status in BENCH_TRANSITION_STATES for status in bench_statuses):
			raise PressWorkflowTaskEnqueued(
				f"Waiting for bench jobs to complete for Deploy Candidate Build {deploy_candidate_build}",
				self.workflow_name,
				self.get_task_name(self.monitor_bench_creation),
			)

	@flow
	def create_release(
		self,
		apps: list[dict[str, str]],
		sites: list[dict[str, Any]],
		run_will_fail_check: bool = False,
	):
		"""Create a release for the release group."""
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
