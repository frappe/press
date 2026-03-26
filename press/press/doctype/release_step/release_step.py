# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt
import typing
from functools import cached_property
from typing import Any

import frappe
from frappe.utils.background_jobs import get_redis_conn
from rq.job import Job, JobStatus, NoSuchJobError

from press.press.doctype.bench_update.bench_update import get_bench_update
from press.workflow_engine.doctype.press_workflow.decorators import flow, task
from press.workflow_engine.doctype.press_workflow.exceptions import PressWorkflowTaskEnqueued
from press.workflow_engine.doctype.press_workflow.workflow_builder import WorkflowBuilder

if typing.TYPE_CHECKING:
	from press.press.doctype.bench_update.bench_update import BenchUpdate
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.release_group.release_group import ReleaseGroup


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
	):
		"""Create a Deploy Candidate for the release group."""
		assert isinstance(self.release_group, str)
		bench_update: BenchUpdate = get_bench_update(
			self.release_group,
			apps,
			sites,
			is_inplace_update=False,
		)
		candidate_name = bench_update.deploy(
			run_will_fail_check=run_will_fail_check,
			validate_pre_candidate_checks=False,
			create_build=create_deploy,
		)
		self.kv.set("candidate", candidate_name)

	@task
	def initiate_pre_build_validations(self):
		"""Clone apps that are to be built in this release."""
		candidate: DeployCandidate = frappe.get_doc("Deploy Candidate", self.kv.get("candidate"))
		deploy_candidate_build = candidate.schedule_build_and_deploy()
		self.kv.delete("candidate")
		self.kv.set("deploy_candidate_build", deploy_candidate_build["name"])
		self.start_and_monitor_pre_build_validation()

	@task
	def start_and_monitor_pre_build_validation(self):
		"""Monitors the Deploy Candidate Build until the remote build job is created."""
		deploy_candidate_build_name = self.kv.get("deploy_candidate_build")
		job_id = f"deploy_candidate_build:{deploy_candidate_build_name}"

		try:
			job = Job.fetch(job_id, connection=get_redis_conn())
			job_status = job.get_status()
		except NoSuchJobError:
			raise PressWorkflowTaskEnqueued(
				f"Waiting for remote build job to be enqueued for Deploy Candidate Build {deploy_candidate_build_name}"
			) from None  # Raise a completely new exception without chaining so that the workflow engine is not confused

		if job_status in [JobStatus.QUEUED, JobStatus.SCHEDULED, JobStatus.STARTED]:
			raise PressWorkflowTaskEnqueued(
				f"Waiting for build job to complete from Deploy Candidate Build {deploy_candidate_build_name}"
			)

		if job_status == JobStatus.FINISHED:
			return  # Pre Build Validation completed can mark as success and proceed

		if job_status == JobStatus.FAILED:
			raise Exception(
				f"Pre Build Validation failed for Deploy Candidate Build {deploy_candidate_build_name}. Please check the build logs for more details."
			)

	@task
	def monitor_remote_build_job(self):
		"""Monitor the remote build agent job until terminal state is reached."""
		...

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
		self.create_deploy_candidate(
			apps=apps,
			sites=sites,
			run_will_fail_check=run_will_fail_check,
			create_deploy=False,
		)
		self.initiate_pre_build_validations()
		self.monitor_remote_build_job()
