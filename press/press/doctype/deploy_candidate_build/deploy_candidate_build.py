# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
# We currently don't take build steps into account.
from __future__ import annotations

import base64
import contextlib
import glob
import json
import os
import re
import shutil
import tempfile
import typing
from datetime import datetime, timedelta
from enum import Enum
from functools import cached_property
from typing import TypedDict
from urllib.parse import quote

import frappe
import requests
import semantic_version
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import now_datetime as now
from frappe.utils import rounded
from tenacity import retry, stop_after_attempt, wait_fixed

from press.agent import Agent
from press.exceptions import ImageNotFoundInRegistry
from press.press.doctype.deploy_candidate.deploy_notifications import (
	create_build_failed_notification,
	create_build_warning_notification,
)
from press.press.doctype.deploy_candidate.docker_output_parsers import (
	CloneOutputParser,
	DockerBuildOutputParser,
	UploadStepUpdater,
	ValidationOutputParser,
)
from press.press.doctype.deploy_candidate.utils import (
	get_arm_build_server_with_least_active_builds,
	get_build_server,
	get_intel_build_server_with_least_active_builds,
	is_suspended,
)
from press.utils import get_current_team, log_error
from press.utils.webhook import create_webhook_event

if typing.TYPE_CHECKING:
	from warnings import WarningMessage

	from rq.job import Job

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_source.app_source import AppSource
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.press_settings.press_settings import PressSettings
	from press.press.doctype.release_group_server.release_group_server import ReleaseGroupServer

# build_duration, pending_duration are Time fields, >= 1 day is invalid
MAX_DURATION = timedelta(hours=23, minutes=59, seconds=59)
DISTUTILS_SUPPORTED_VERSION = semantic_version.SimpleSpec("<3.12")
GET_PIP_VERSION_MODIFIED_URL = semantic_version.SimpleSpec(">=3.2,<=3.8")
ARM_SUPPORTED_WKHTMLTOPDF = ["0.12.5", "0.12.6"]


class Status(Enum):
	FAILURE = "Failure"
	SUCCESS = "Success"
	PENDING = "Pending"
	RUNNING = "Running"
	SCHEDULED = "Scheduled"
	PREPARING = "Preparing"
	DRAFT = "Draft"

	@classmethod
	def terminal(cls):
		return [cls.FAILURE.value, cls.SUCCESS.value]

	@classmethod
	def intermediate(cls):
		return [cls.PENDING.value, cls.RUNNING.value, cls.PREPARING.value]


STAGE_SLUG_MAP = {
	"clone": "Clone Repositories",
	"pre_before": "Run Before Prerequisite Script",
	"pre": "Setup Prerequisites",
	"pre_after": "Run After Prerequisite Script",
	"bench": "Setup Bench",
	"apps": "Install Apps",
	"validate": "Run Validations",
	"pull": "Pull Updates",
	"mounts": "Setup Mounts",
	"upload": "Upload",
}

# Key: (stage_slug, step_slug)
STEP_SLUG_MAP = {
	("pre", "essentials"): "Install Essential Packages",
	("pre", "redis"): "Install Redis",
	("pre", "python"): "Install Python",
	("pre", "wkhtmltopdf"): "Install wkhtmltopdf",
	("pre", "fonts"): "Install Fonts",
	("pre", "node"): "Install Node.js",
	("pre", "yarn"): "Install Yarn",
	("pre", "pip"): "Install pip",
	("pre", "code-server"): "Install Code Server",
	("bench", "bench"): "Install Bench",
	("bench", "env"): "Setup Virtual Environment",
	("validate", "pre-build"): "Pre-build",
	("validate", "dependencies"): "Validate Dependencies",
	("mounts", "create"): "Prepare Mounts",
	("upload", "image"): "Docker Image",
}


class AssetStoreCredentials(TypedDict):
	secret_access_key: str
	access_key: str
	region_name: str
	endpoint_url: str
	bucket_name: str


def get_asset_store_credentials() -> AssetStoreCredentials:
	"""Return asset store credentials from Press Settings."""
	settings: PressSettings = frappe.get_cached_doc("Press Settings")

	return {
		"secret_access_key": settings.get_password("asset_store_secret_access_key"),
		"access_key": settings.asset_store_access_key,
		"region_name": settings.asset_store_region,
		"endpoint_url": settings.asset_store_endpoint,
		"bucket_name": settings.asset_store_bucket_name,
	}


def get_build_stage_and_step(
	stage_slug: str, step_slug: str, app_titles: dict[str, str] | None = None
) -> tuple[str, str | None]:
	stage = STAGE_SLUG_MAP.get(stage_slug, stage_slug)
	step = step_slug
	if (stage_slug == "clone" or stage_slug == "apps") and app_titles:
		step = app_titles.get(step_slug, step_slug)
	else:
		step = STEP_SLUG_MAP.get((stage_slug, step_slug), step_slug)
	return (stage, step)


def get_remote_step_output(
	step_name: typing.Literal["build", "push"],
	output_data: dict,
	response_data: dict | None,
):
	if output := output_data.get(step_name):
		return output

	if not isinstance(response_data, dict):
		return None

	job_step_name = "Build Image" if step_name == "build" else "Push Docker Image"
	for step in response_data.get("steps", []):
		if step.get("name") != job_step_name:
			continue

		commands = step.get("commands", [])
		if not isinstance(commands, list) or len(commands) == 0 or not isinstance(commands[0], dict):
			continue

		output = commands[0].get("output")
		if not isinstance(output, str):
			continue

		with contextlib.suppress(AttributeError, json.JSONDecodeError):
			return json.loads(output).get(step_name, [])

	return None


def get_duration(start_time: datetime, end_time: datetime | None = None):
	end_time = end_time or now()
	seconds_elapsed = (end_time - start_time).total_seconds()
	value = rounded(seconds_elapsed, 3)
	return float(value)


class DeployCandidateBuild(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.deploy_candidate_build_step.deploy_candidate_build_step import (
			DeployCandidateBuildStep,
		)

		build_directory: DF.Data | None
		build_duration: DF.Time | None
		build_end: DF.Datetime | None
		build_error: DF.Code | None
		build_output: DF.Code | None
		build_server: DF.Link | None
		build_start: DF.Datetime | None
		build_steps: DF.Table[DeployCandidateBuildStep]
		deploy_after_build: DF.Check
		deploy_candidate: DF.Link
		deploy_on_server: DF.Link | None
		docker_image: DF.Data | None
		docker_image_id: DF.Data | None
		docker_image_repository: DF.Data | None
		docker_image_tag: DF.Data | None
		error_key: DF.Data | None
		group: DF.Link
		manually_failed: DF.Check
		no_build: DF.Check
		no_cache: DF.Check
		no_push: DF.Check
		pending_duration: DF.Time | None
		pending_end: DF.Datetime | None
		pending_start: DF.Datetime | None
		platform: DF.Data | None
		retry_count: DF.Int
		run_build: DF.Check
		scheduled_time: DF.Datetime | None
		status: DF.Literal["Draft", "Scheduled", "Pending", "Preparing", "Running", "Success", "Failure"]
		team: DF.Link
		user_addressable_failure: DF.Check
	# end: auto-generated types

	dashboard_fields = (
		"name",
		"status",
		"creation",
		"deployed",
		"build_steps",
		"build_start",
		"build_end",
		"build_duration",
		"build_error",
		"group",
		"retry_count",
		"team",
		"deploy_candidate",
	)

	@cached_property
	def candidate(self) -> DeployCandidate:
		return frappe.get_doc("Deploy Candidate", self.deploy_candidate)

	def set_status(
		self,
		status: Status,
		timestamp_field: str | None = None,
		commit: bool = False,
	):
		self.status = status.value

		if self.status == Status.FAILURE.value:
			self._fail_last_running_step()

		if timestamp_field and hasattr(self, timestamp_field):
			setattr(self, timestamp_field, now())

		self.save(ignore_version=True)

		if commit:
			frappe.db.commit()

	def _get_dockerfile_checkpoints(self, dockerfile: str) -> list[str]:
		"""
		Returns checkpoint slugs from a generated Dockerfile
		"""

		# Example: "`#stage-pre-essentials`", "`#stage-apps-print_designer`"
		rx = re.compile(r"`#stage-([^`]+)`")

		# Example: "pre-essentials", "apps-print_designer"
		checkpoints = []
		for line in dockerfile.split("\n"):
			matches = rx.findall(line)
			checkpoints.extend(matches)

		return checkpoints

	def _parse_python_version(self, version: str) -> semantic_version.Version:
		try:
			python_version = semantic_version.Version(version)
		except ValueError:
			python_version = semantic_version.Version(f"{version}.0")
		return python_version

	def check_distutils_support(self, version: str) -> bool:
		"""
		Checks if specified python version supports distutils.
		"""
		python_version = self._parse_python_version(version)
		return python_version in DISTUTILS_SUPPORTED_VERSION

	def check_get_pip_url_support(self, version: str) -> bool:
		"""
		Checks if specified python version can be fetched from get-pip
		"""
		python_version = self._parse_python_version(version)
		return python_version in GET_PIP_VERSION_MODIFIED_URL

	def _generate_dockerfile(self) -> str:
		dockerfile_template = "press/docker/Dockerfile"
		is_distutils_supported = True
		requires_version_based_get_pip = False

		for d in self.candidate.dependencies:
			if d.dependency == "PYTHON_VERSION":
				is_distutils_supported = self.check_distutils_support(d.version)
				requires_version_based_get_pip = self.check_get_pip_url_support(d.version)

			if d.dependency == "BENCH_VERSION" and d.version == "5.2.1":
				dockerfile_template = "press/docker/Dockerfile_Bench_5_2_1"

		return frappe.render_template(
			dockerfile_template,
			{
				"doc": self.candidate,
				"remove_distutils": not is_distutils_supported,
				"requires_version_based_get_pip": requires_version_based_get_pip,
				"is_arm_build": self.platform == "arm64",
				"use_asset_store": False,
				"upload_assets": False,
				"site_url": frappe.utils.get_url(),
			},
			is_path=True,
		)

	def add_post_build_steps(self):
		slugs = []

		if not self.no_push:
			slugs.append(("upload", "image"))

		for stage_slug, step_slug in slugs:
			stage, step = get_build_stage_and_step(stage_slug, step_slug, {})
			step = dict(
				status="Pending",
				stage_slug=stage_slug,
				step_slug=step_slug,
				stage=stage,
				step=step,
			)
			self.append("build_steps", step)

		self.save()

	def add_pre_build_steps(self):
		app_titles = {a.app: a.title for a in self.candidate.apps}

		# Clone app slugs
		slugs: list[tuple[str, str]] = [("clone", app.app) for app in self.candidate.apps]

		slugs.extend([("validate", "pre-build")])

		for stage_slug, step_slug in slugs:
			stage, step = get_build_stage_and_step(
				stage_slug,
				step_slug,
				app_titles,
			)
			step_dict = dict(
				status="Pending",
				stage_slug=stage_slug,
				step_slug=step_slug,
				stage=stage,
				step=step,
			)
			self.append("build_steps", step_dict)

		self.save()

	def add_build_steps(self, dockerfile: str):
		app_titles = {a.app: a.title for a in self.candidate.apps}

		checkpoints = self._get_dockerfile_checkpoints(dockerfile)
		for checkpoint in checkpoints:
			splits = checkpoint.split("-", 1)
			if len(splits) != 2:
				continue

			stage_slug, step_slug = splits
			stage, step = get_build_stage_and_step(
				stage_slug,
				step_slug,
				app_titles,
			)

			self.append(
				"build_steps",
				dict(
					status="Pending",
					stage_slug=stage_slug,
					step_slug=step_slug,
					stage=stage,
					step=step,
				),
			)

		self.save()

	def _flush_output_parsers(self, commit=False):
		if self.build_output_parser:
			self.build_output_parser.flush_output(commit)

		if self.upload_step_updater:
			self.upload_step_updater.flush_output(commit)

	def _set_output_parsers(self):
		self.clone_output_parser = CloneOutputParser(self)
		self.validation_output_parser = ValidationOutputParser(self)
		self.build_output_parser = DockerBuildOutputParser(self)
		self.upload_step_updater = UploadStepUpdater(self)

	def correct_upload_step_status(self):
		if not (usu := self.upload_step_updater) or not usu.upload_step:
			return

		if self.status == "Success" and usu.upload_step.status == "Running":
			self.upload_step_updater.end("Success")

		elif self.status == "Failure" and usu.upload_step.status not in [
			"Failure",
			"Pending",
		]:
			self.upload_step_updater.end("Pending")

	def get_first_step(self, key: str, value: str | list[str]) -> "DeployCandidateBuildStep | None":
		if isinstance(value, str):
			value = [value]

		for build_step in self.build_steps:
			if build_step.get(key) not in value:
				continue
			return build_step
		return None

	def has_remote_build_failed(self, job: "AgentJob", job_data: dict) -> bool:
		if job.status == "Failure":
			return True

		if job_data.get("build_failed"):
			return True

		if (usu := self.upload_step_updater) and usu.upload_step and usu.upload_step.status == "Failure":
			return True

		if self.get_first_step("status", "Failure"):
			return True

		return False

	def should_build_retry(
		self,
		exc: Exception | None,
		job: "AgentJob | None",
	) -> bool:
		if self.status != "Failure":
			return False

		# Retry twice before giving up
		if self.retry_count >= 3:
			return False

		bo = self.build_output
		if isinstance(bo, str) and should_build_retry_build_output(bo):
			return True

		if exc and should_build_retry_exc(exc):
			return True

		if job and should_build_retry_job(job):
			return True

		return False

	def handle_build_warning(self, title, warning: "WarningMessage") -> None:
		"""Create warning notification similar to error notifications"""
		create_build_warning_notification(
			dc=self.candidate,
			dcb=self,
			title=title,
			message=warning.message,
		)

	def handle_build_failure(
		self,
		exc: Exception | None = None,
		job: AgentJob | None = None,
	) -> None:
		self._flush_output_parsers()
		self.set_status(Status.FAILURE)
		self._set_build_duration()

		should_retry = self.should_build_retry(exc=exc, job=job)

		if not should_retry:
			self.candidate._fail_site_group_deploy_if_exists()

		# Do not send a notification if the build is being retried.
		if not should_retry and create_build_failed_notification(self.candidate, self, exc):
			self.user_addressable_failure = True
			self.save(ignore_permissions=True)
			frappe.db.commit()
			return

		if should_retry:
			self.schedule_build_retry()
			return

		if exc:
			# Log and raise error if build failure is not actionable or no retry
			log_error("Deploy Candidate Build Exception", doc=self)

	def schedule_build_retry(self):
		"""
		Fail the current deploy candidate build and create a new deploy candidate build
		with an increased `retry_count` and a scheduled time.
		"""
		minutes = min(5**self.retry_count, 125)
		scheduled_time = now() + timedelta(minutes=minutes)
		self.set_status(Status.FAILURE)
		# Increase the retry count
		if self.retry_count < 3:
			self.candidate.schedule_build_and_deploy(
				run_now=False, scheduled_time=scheduled_time, retry_count=self.retry_count + 1
			)

	@retry(
		reraise=True,
		wait=wait_fixed(300),
		stop=stop_after_attempt(3),
	)
	def upload_build_context_for_docker_build(
		self,
		context_filepath: str,
		build_server: str,
	):
		agent = Agent(build_server)
		with open(context_filepath, "rb") as file:
			if upload_filename := agent.upload_build_context_for_docker_build(file, self.name):
				return upload_filename

		message = "Failed to upload build context to remote docker builder"
		if agent.response:
			message += f"\nagent response: {agent.response.text}"

		raise Exception(message)

	def _set_pending_duration(self):
		self.pending_end = now()
		if not isinstance(self.pending_start, datetime):
			return

		self.pending_duration = min(
			self.pending_end - self.pending_start,
			MAX_DURATION,
		)

	def _set_build_duration(self):
		self.build_end = now()
		if not isinstance(self.build_start, datetime):
			return

		self.build_duration = min(
			self.build_end - self.build_start,
			MAX_DURATION,
		)

	def _fail_last_running_step(self):
		for step in self.build_steps:
			if step.status == "Failure":
				return

			if step.status == "Running":
				step.status = "Failure"
				break

	def _update_status_from_remote_build_job(self, job: "AgentJob"):
		match job.status:
			case "Pending" | "Running":
				return self.set_status(Status.RUNNING)
			case "Failure" | "Undelivered" | "Delivery Failure":
				self._set_build_duration()
				return self.set_status(Status.FAILURE)
			case "Success":
				self._set_build_duration()
				return self.set_status(Status.SUCCESS)
			case _:
				raise Exception("unreachable code execution")

	def update_deploy_candidate_with_build(self):
		"""Update the deploy candidate with the build fields"""
		candidate_field = "arm_build" if self.platform == "arm64" else "intel_build"
		setattr(self.candidate, candidate_field, self.name)
		self.candidate.save()

	def create_new_platform_build_if_required_and_deploy(self, deploy_after_build: bool):
		"""Create a platform specific build if requirement enforced by the deploy candidate"""
		requires_arm = self.candidate.requires_arm_build and not self.candidate.arm_build
		requires_intel_build = self.candidate.requires_intel_build and not self.candidate.intel_build

		build_meta = {
			"doctype": "Deploy Candidate Build",
			"deploy_candidate": self.candidate.name,
			"no_build": self.no_build,
			"no_cache": self.no_cache,
			"no_push": self.no_push,
			"deploy_after_build": deploy_after_build,
		}

		if requires_arm:
			build_meta.update({"platform": "arm64"})
			frappe.get_doc(build_meta).insert()
		if requires_intel_build:
			build_meta.update({"platform": "x86_64"})
			frappe.get_doc(build_meta).insert()

		if (
			not requires_arm
			and not requires_intel_build
			and self.status == Status.SUCCESS.value
			and deploy_after_build
		):
			self.create_deploy()

	@staticmethod
	def process_run_build(job: AgentJob, response_data: dict | None):
		request_data = json.loads(job.request_data)
		build: DeployCandidateBuild = frappe.get_doc(
			"Deploy Candidate Build", request_data["deploy_candidate_build"]
		)
		build._process_run_build(job, request_data, response_data)

		if build.status == Status.SUCCESS.value:
			build.update_deploy_candidate_with_build()

			deploy_on_server = request_data.get("deploy_on_server")
			if deploy_on_server:
				build._create_deploy([deploy_on_server])
				return

			build.create_new_platform_build_if_required_and_deploy(
				deploy_after_build=request_data.get("deploy_after_build")
			)

	def get_all_pending_clone_steps(self) -> list["DeployCandidateBuildStep"]:
		"""Return all the pending clone steps"""
		return [
			step
			for step in self.build_steps
			if step.stage_slug == "clone" and step.status not in ["Success", "Failure"]
		]

	def has_failed_clone_steps(self) -> bool:
		return any(
			step for step in self.build_steps if step.stage_slug == "clone" and step.status == "Failure"
		)

	def _process_run_build(
		self,
		job: "AgentJob",
		request_data: dict,
		response_data: dict | None,
	):
		job_data = json.loads(job.data or "{}")
		job_data_output = job_data.get("output", "{}")
		output_data = json.loads(job_data_output) if isinstance(job_data_output, str) else job_data_output
		"""
		Due to how agent - press communication takes place, every time an
		output is published all of it has to be re-parsed from the start.

		This is due to a method of streaming agent output to press not
		existing.
		"""
		self._set_output_parsers()
		clone_failed = self.clone_output_parser.parse_clone_output_and_update_step(
			job,
		)

		if not clone_failed:
			try:
				self.validation_output_parser.parse_validation_output_and_update_step(
					job,
				)
			except Exception as e:
				self.handle_build_failure(exc=e, job=job)
				return  # Handle this just like we handled when working on press directly

		if not clone_failed:
			if output := get_remote_step_output(
				"build",
				output_data,
				response_data,
			):
				self.build_output_parser.parse_and_update(output)

			if output := get_remote_step_output(
				"push",
				output_data,
				response_data,
			):
				self.upload_step_updater.start()
				self.upload_step_updater.process(output)

		if self.has_remote_build_failed(job, job_data):
			self.handle_build_failure(exc=None, job=job)
		else:
			self._update_status_from_remote_build_job(job)

		# Fallback case cause upload step can be left hanging
		self.correct_upload_step_status()

	def get_step(self, stage_slug: str, step_slug: str) -> "DeployCandidateBuildStep | None":
		return find(
			self.build_steps,
			lambda x: x.stage_slug == stage_slug and x.step_slug == step_slug,
		)

	def _fetch_registry_settings(self):
		return frappe.db.get_value(
			"Press Settings",
			None,
			[
				"domain",
				"docker_registry_url",
				"docker_registry_namespace",
				"docker_registry_username",
				"docker_registry_password",
			],
			as_dict=True,
		)

	def _update_docker_image_metadata(self):
		settings = self._fetch_registry_settings()

		if settings.docker_registry_namespace:
			namespace = f"{settings.docker_registry_namespace}/{settings.domain}"
		else:
			namespace = f"{settings.domain}"

		self.docker_image_repository = f"{settings.docker_registry_url}/{namespace}/{self.group}"
		self.docker_image_tag = self.name
		self.docker_image = f"{self.docker_image_repository}:{self.docker_image_tag}"

	def check_image_in_registry(self) -> bool:
		"""Check if the image tag exists on registry"""
		settings = self._fetch_registry_settings()

		if settings.docker_registry_url != "registry.frappe.cloud":
			return True

		return is_image_in_registry(self.name, self.group, settings)

	def encode_dockerfile(self, dockerfile):
		"""Encode dockerfile content to base64 to be sent to agent"""
		dockerfile_bytes = dockerfile.encode("utf-8")
		return base64.b64encode(dockerfile_bytes).decode("utf-8")

	def send_build_instructions_and_add_build_steps(self):
		"""
		Prepare build instructions and mark ready to upload also adds the build and post build steps

		HOW IT WORKS:
		-------------
		1. Get all the app sources part of the deploy candidate.
		2. Get all app releases part of the deploy candidate.
		3. Get the required repo urls (with token for private repos) of the app releases.
		4. Generate the dockerfile
		"""
		clone_instructions = []

		for app in self.candidate.apps:
			app_source = app.source
			app_release = app.release

			hash = frappe.db.get_value("App Release", app_release, "hash")
			source: "AppSource" = frappe.get_doc("App Source", app_source)
			url = source.get_repo_url()
			clone_instructions.append(
				{
					"app": app.app,
					"url": url,
					"release": app_release,
					"source": app_source,
					"hash": hash,
					"branch": source.branch,
				}
			)

		dockerfile = self._generate_dockerfile()
		# Add build steps based on dockerfile checkpoints before starting the build
		self.add_build_steps(dockerfile)
		self.add_post_build_steps()

		encoded_dockerfile = self.encode_dockerfile(dockerfile)
		settings = self._fetch_registry_settings()
		dependencies = {d.dependency: d.version for d in self.candidate.dependencies}
		self._update_docker_image_metadata()

		build_parameters = {
			"image_repository": self.docker_image_repository,
			"image_tag": self.docker_image_tag,
			"registry": {
				"url": settings.docker_registry_url,
				"username": settings.docker_registry_username,
				"password": settings.docker_registry_password,
			},
			"no_cache": self.no_cache,
			"no_push": self.no_push,
			"build_token": self.candidate.build_token,
			# Next few values are not used by agent but are
			# read in `process_run_build`
			"deploy_candidate_build": self.name,
			"deploy_after_build": self.deploy_after_build,
			"deploy_on_server": self.deploy_on_server,
			# Used by agent to prepare build context
			"dockerfile": encoded_dockerfile,
			"clone_instructions": clone_instructions,
			"build_name": self.name,
			"group": self.group,
			"deploy_candidate_params": {
				"redis_cache_size": self.candidate.redis_cache_size,
				"is_redisearch_enabled": self.candidate.is_redisearch_enabled,
				"environment_variables": self.candidate.environment_variables,
				"use_rq_workerpool": self.candidate.use_rq_workerpool,
				"merge_all_rq_queues": self.candidate.merge_all_rq_queues,
				"merge_default_and_short_rq_queues": self.candidate.merge_default_and_short_rq_queues,
				"custom_workers": self.candidate.custom_workers,
				"custom_workers_group": self.candidate.custom_workers_group,
				"is_code_server_enabled": False,  # We no longer seem to use this since code server runs on press
				"is_ssh_enabled": False,  # Set by bench when creating container
				"dependencies": dependencies,
			},
		}
		if self.platform == "arm64":
			build_parameters.update({"platform": self.platform})

		Agent(self.build_server).run_build(build_parameters)

	def build(self):
		self._set_pending_duration()
		self.set_status(
			Status.PREPARING,
			timestamp_field="build_start",
			commit=True,
		)
		self._set_output_parsers()
		self.send_build_instructions_and_add_build_steps()
		self.set_status(Status.RUNNING, commit=True)

	def reset_build_state(self):
		self.cleanup_build_directory()
		self.build_steps.clear()
		self.build_directory = None
		self.build_error = ""
		self.build_output = ""
		# Failure flags
		self.user_addressable_failure = False
		self.manually_failed = False
		# Build times
		self.build_start = None
		self.build_end = None
		self.build_duration = None
		# Pending times
		self.pending_start = None
		self.pending_end = None
		self.pending_duration = None

	def get_platform(self) -> str:
		return frappe.get_value("Server", self.build_server, "platform")

	def _select_build_server(self):
		"""Select build server based on platform or group"""
		match self.platform:
			case "arm64":
				return get_arm_build_server_with_least_active_builds()
			case "x86_64":
				return get_intel_build_server_with_least_active_builds()
			case _:
				# Case where no platform is set?
				# The first build that occurs will be based on the platform of first
				# Server listed in the Release Group Server List
				# Then if anyother builds are required their platform will be passed in.
				return get_build_server(self.group)

	def set_platform(self):
		# If no platform is set we set the platform based on the build server
		if not self.platform:
			self.platform = self.get_platform() or "x86_64"

	def set_build_server(self):
		if not self.build_server:
			self.build_server = self._select_build_server()

		if self.build_server:
			self.set_platform()

		if self.build_server or self.no_build:
			return

		throw_no_build_server()

	def validate_status(self):
		if self.status in ["Draft", "Success", "Failure", "Scheduled"]:
			return True

		frappe.throw(
			f"Build is in <b>{self.status}</b> state. "
			"Please wait for build to succeed or fail before retrying."
		)
		return False

	def get_team_for_build(self):
		"""Default to group team in case of new flow"""
		new_flow = frappe.db.get_single_value("Press Settings", "use_new_deploy_flow")
		return (
			frappe.db.get_value("Release Group", self.group, "team") if new_flow else get_current_team(True)
		)

	def pre_build(self, **kwargs):
		self.reset_build_state()
		self.add_pre_build_steps()

		if not self.validate_status():
			return

		if "no_cache" in kwargs:
			self.no_cache = kwargs.get("no_cache")
			del kwargs["no_cache"]

		self.set_build_server()
		self.set_status(Status.PENDING, timestamp_field="pending_start")

		self.save()

		(
			user,
			session_data,
			team,
		) = (
			frappe.session.user,
			frappe.session.data,
			self.get_team_for_build(),
		)

		frappe.set_user(frappe.get_value("Team", team if isinstance(team, str) else team.name, "user"))

		self.build()

		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	def on_update(self):
		if self.status == "Running":
			frappe.publish_realtime(
				f"bench_deploy:{self.name}:steps",
				doctype=self.doctype,
				docname=self.name,
				message={"steps": self.build_steps, "name": self.name},
			)
		else:
			frappe.publish_realtime(
				f"bench_deploy:{self.name}:finished",
				doctype=self.doctype,
				docname=self.name,
			)

		if self.has_value_changed("status") and self.team != "Administrator":
			create_webhook_event("Bench Deploy Status Update", self, self.team)

	def run_scheduled_build_and_deploy(self):
		self.set_status(Status.DRAFT)
		self.pre_build()

	def after_insert(self):
		if self.run_build and self.status != Status.SCHEDULED.value:
			self.set_status(Status.DRAFT)
			self.pre_build()

	def _stop_and_fail(self):
		"""Since we are relying on remote builder completely, we can just mark the build as
		manually failed and the remote builder will stop the build when it checks the status"""
		fail_remote_job(self.name)

	def create_deploy(self, check_image_exists: bool = False):
		"""Create a new deploy for the servers of matching platform present on the release group"""
		servers: list[ReleaseGroupServer] = frappe.get_doc("Release Group", self.group).servers
		servers = [server.server for server in servers]

		if not servers:
			return None

		deploy_doc = frappe.db.exists(
			"Deploy", {"group": self.group, "candidate": self.name, "staging": False}
		)

		if deploy_doc:
			return str(deploy_doc)

		return self._create_deploy(servers, check_image_exists=check_image_exists).name

	def _create_deploy(self, servers: list[str], check_image_exists: bool = False):
		if check_image_exists and not self.check_image_in_registry():
			frappe.throw("Image not found in registry create a new build", ImageNotFoundInRegistry)

		return frappe.get_doc(
			{
				"doctype": "Deploy",
				"group": self.group,
				"candidate": self.deploy_candidate,
				"benches": [{"server": server} for server in servers],
			}
		).insert()

	@frappe.whitelist()
	def deploy(self):
		try:
			return dict(
				error=False, message=self.create_deploy(check_image_exists=True)
			)  # In this case we can check if image is in registry since possible to deploy older builds
		except Exception:
			log_error("Deploy Creation Error", doc=self)

	@frappe.whitelist()
	def redeploy(self, no_cache: bool = False):
		deploy_candidate: DeployCandidate | None = self.candidate.get_duplicate_dc()
		if not deploy_candidate:
			return dict(error=True, message="Cannot create duplicate Deploy Candidate")

		deploy_candidate_build_name = deploy_candidate.build_and_deploy(no_cache=no_cache)
		return dict(error=False, message=deploy_candidate_build_name)

	@frappe.whitelist()
	def cleanup_build_directory(self):
		if not self.build_directory:
			return

		if os.path.exists(self.build_directory):
			shutil.rmtree(self.build_directory)

		self.build_directory = None
		self.save()

	def get_steps(self):
		steps = []
		# Expand the build steps
		for s in self.build_steps:
			steps.append(
				{
					"name": f"{s.stage_slug}_{s.step_slug}",
					"title": s.step.title(),
					"status": s.status,
					"output": s.output,
					"stage": "Bench Build",
				}
			)

		# Expand the bench deploy steps if deploy exists
		if frappe.flags.site_action_args and (bench := frappe.flags.site_action_args.get("cloned_bench")):
			bench = frappe.get_doc("Bench", bench)
			steps.extend(bench.get_steps())
		return steps


@frappe.whitelist()
def stop_and_fail(dn: str):
	# We can avoid lock here in testing it did not raise a timestamp mismatch error.
	build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dn)
	if build.status in Status.intermediate():
		build._stop_and_fail()


@frappe.whitelist()
def fail_and_redeploy(dn: str):
	stop_and_fail(dn)

	build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dn)

	return build.redeploy()


@frappe.whitelist()
def redeploy(dn: str) -> dict[str, str | bool]:
	"""Allow redeploy preserving app sources if the deploy is in terminal stage"""
	deploy_candidate_build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dn)

	if deploy_candidate_build.status in Status.intermediate():
		frappe.throw(
			"Wait for deploy to finish or stop current deploy first!",
			frappe.ValidationError,
		)

	return deploy_candidate_build.redeploy()


@frappe.whitelist()
def fail_remote_job(dn: str) -> bool:
	agent_job: "AgentJob" = frappe.get_doc(
		"Agent Job", {"reference_doctype": "Deploy Candidate Build", "reference_name": dn}
	)

	agent_job.get_status()
	agent_job = agent_job.reload()

	if agent_job.status in ["Success", "Failure"]:
		# We can't do anything here since the job is already in a terminal state
		return False

	if agent_job.status in ["Pending", "Undelivered"]:
		# Return true since the job is now failed and will not be retried by agent
		agent_job.fail_and_process_job_updates()

	if agent_job.status == "Running":
		# Cancel build and set status with for_update and commit to avoid timestamp errors
		agent_job.cancel_job()

	build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dn, for_update=True)
	build.manually_failed = True
	build.set_status(Status.FAILURE)
	frappe.db.commit()

	return True


def is_build_job(job: Job) -> bool:
	doc_method: str = job.kwargs.get("kwargs", {}).get("doc_method", "")
	return doc_method.startswith("_build")


def should_build_retry_build_output(build_output: str):
	# Build failed cause APT could not get lock.
	if "Could not get lock /var/cache/apt/archives/lock" in build_output:
		return True

	# Build failed cause Docker could not find a mounted file/folder
	if "failed to compute cache key: failed to calculate checksum of ref" in build_output:
		return True

	# Failed to pull package from pypi
	if "Connection to pypi.org timed out" in build_output:
		return True

	# Caused when fetching Python from deadsnakes/ppa
	if "Error: retrieving gpg key timed out" in build_output:
		return True

	# Yarn registry bad gateway
	if (
		"error https://registry.yarnpkg.com/" in build_output
		and 'Request failed "502 Bad Gateway"' in build_output
	):
		return True

	# NPM registry internal server error
	if (
		"Error: https://registry.npmjs.org/" in build_output
		and 'Request failed "500 Internal Server Error"' in build_output
	):
		return True

	return False


def should_build_retry_exc(exc: Exception):
	error = frappe.get_traceback(False)
	if not error and len(exc.args) == 0:
		return False

	error = error or "\n".join(str(a) for a in exc.args)

	# Failed to upload build context (Mostly 502)
	if "Failed to upload build context" in error:
		return True

	# Redis refused connection (press side)
	if "redis.exceptions.ConnectionError: Error 111" in error:
		return True

	if "rq.timeouts.JobTimeoutException: Task exceeded maximum timeout value" in error:
		return True

	return False


def should_build_retry_job(job: "AgentJob"):
	if not job.traceback:
		return False

	# Failed to upload docker image
	if "TimeoutError: timed out" in job.traceback:
		return True

	# Redis connection reset
	if "ConnectionResetError: [Errno 104] Connection reset by peer" in job.traceback:
		return True

	# Redis connection refused
	if "ConnectionRefusedError: [Errno 111] Connection refused" in job.traceback:
		return True

	return False


def run_scheduled_builds(max_builds: int = 5):
	if is_suspended():
		return

	dcs = frappe.get_all(
		"Deploy Candidate Build",
		{
			"status": "Scheduled",
			"scheduled_time": ("<=", frappe.utils.now_datetime()),
		},
		pluck="name",
		limit=max_builds,
	)
	for dc in dcs:
		doc: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dc)
		try:
			doc.run_scheduled_build_and_deploy()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Scheduled Deploy Candidate Error", doc=doc)


def create_platform_build_and_deploy(deploy_candidate: str, server: str, platform: str) -> str:
	"""Create an arm / intel build and trigger a deploy on the given server"""
	deploy_candidate_build: DeployCandidateBuild = frappe.get_doc(
		{
			"doctype": "Deploy Candidate Build",
			"deploy_candidate": deploy_candidate,
			"no_build": False,
			"no_cache": False,
			"no_push": False,
			"platform": platform,
			"deploy_on_server": server,
		}
	)
	build = deploy_candidate_build.insert()
	return build.name


def check_builds_status(
	last_n_days=0,
	last_n_hours=4,
	stuck_threshold_in_hours=2,
):
	fail_or_retry_stuck_builds(
		last_n_days=last_n_days,
		last_n_hours=last_n_hours,
		stuck_threshold_in_hours=stuck_threshold_in_hours,
	)
	correct_false_positives(
		last_n_days=last_n_days,
		last_n_hours=last_n_hours,
	)
	frappe.db.commit()


def fail_or_retry_stuck_builds(
	last_n_days=0,
	last_n_hours=4,
	stuck_threshold_in_hours=2,
):
	# Fails or retries builds builds from the `last_n_days` and `last_n_hours` that
	# have not been updated for longer than `stuck_threshold_in_hours`.
	result = frappe.db.sql(
		"""
	select dcb.name as name
	from  `tabDeploy Candidate Build` as dcb
	where  dcb.modified between now() - interval %s day - interval %s hour and now()
	and    dcb.modified < now() - interval %s hour
	and    dcb.status not in ('Draft', 'Failure', 'Success')
	""",
		(
			last_n_days,
			last_n_hours,
			stuck_threshold_in_hours,
		),
	)

	for (name,) in result:
		dcb: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", name)
		dcb._stop_and_fail()
		dcb = dcb.reload()  # Stop and fail makes modifications to the build

		if can_retry_build(dcb.name, dcb.group, dcb.build_start):
			dcb.schedule_build_retry()


def can_retry_build(name: str, group: str, build_start: datetime):
	# Can retry only if build was started today and
	# if no builds were started after the current build.
	if build_start.date().isoformat() != frappe.utils.today():
		return False

	result = frappe.db.count(
		"Deploy Candidate Build",
		filters={
			"group": group,
			"build_start": [">", build_start],
			"name": ["!=", name],  # sanity filter
		},
	)

	if isinstance(result, int):
		return result == 0
	return False


def correct_false_positives(last_n_days=0, last_n_hours=1):
	# Fails jobs non Failed jobs that have steps with Failure status
	result = frappe.db.sql(
		"""
	with dcb as (
		select dcb.name as name, dcb.status as status
		from  `tabDeploy Candidate Build` as dcb
		where  dcb.modified between now() - interval %s day - interval %s hour and now()
		and    dcb.status != "Failure"
	)
	select dcb.name
	from   dcb join `tabDeploy Candidate Build Step` as deploy_candidate_build_step
	on     dcb.name = deploy_candidate_build_step.parent
	where  deploy_candidate_build_step.status = "Failure"
	""",
		(
			last_n_days,
			last_n_hours,
		),
	)

	for (name,) in result:
		correct_status(name)


def cleanup_build_directories():
	# Cleanup Build Directories for Deploy Candidate Builds older than a day
	dcs = frappe.get_all(
		"Deploy Candidate Build",
		{
			"status": ("!=", "Draft"),
			"build_directory": ("is", "set"),
			"creation": ("<=", frappe.utils.add_to_date(None, hours=-6)),
		},
		order_by="creation asc",
		pluck="name",
		limit=100,
	)
	for dc in dcs:
		doc: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dc)
		try:
			doc.cleanup_build_directory()
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			log_error(title="Deploy Candidate Build Cleanup Error", exception=e, doc=doc)

	# Delete all temporary files created by the build process
	glob_path = os.path.join(tempfile.gettempdir(), f"{tempfile.gettempprefix()}*.tar.gz")
	six_hours_ago = frappe.utils.add_to_date(None, hours=-6)
	for file in glob.glob(glob_path):
		# Use local time to compare timestamps
		if os.stat(file).st_ctime < six_hours_ago.timestamp():
			os.remove(file)


def correct_status(dcb_name: str):
	dcb: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", dcb_name)
	found_failed = False
	for bs in dcb.build_steps:
		if bs.status == "Failure":
			found_failed = True
			continue

		if not found_failed:
			continue

		bs.status = "Pending"

	if not found_failed:
		return

	dcb._stop_and_fail()


def throw_no_build_server():
	frappe.throw(
		"Server not found to run builds. "
		"Please set <b>Build Server</b> under <b>Press Settings > Docker > Docker Build</b>."
	)


def _create_arm_build(deploy_candidate: str) -> DeployCandidateBuild:
	"""This is a utility to create an ARM build for all benches on a server."""

	deploy_candidate_build: DeployCandidateBuild = frappe.get_doc(
		{
			"doctype": "Deploy Candidate Build",
			"deploy_candidate": deploy_candidate,
			"no_build": False,
			"no_cache": False,
			"no_push": False,
			"platform": "arm64",
		}
	)
	arm_build = deploy_candidate_build.insert()
	# Even if arm_build is not required on this deploy candidate we still attach it here
	# Since we don't want loose builds
	frappe.db.set_value("Deploy Candidate", {"name": deploy_candidate}, "arm_build", arm_build.name)
	return arm_build.name


def query_digitalocean_registry(image: str, group: str, settings: dict[str, str]) -> bool:
	headers = {
		"Authorization": f"Bearer {settings['docker_registry_password']}",
		"Accept": "Content-Type: application/json",
	}
	repo = f"{settings['domain']}/{group}"
	encoded_repo = quote(repo, safe="")

	url = (
		"https://api.digitalocean.com/v2/registry/"
		f"{settings['docker_registry_namespace']}/repositories/{encoded_repo}/tags"
	)

	response = requests.get(url, headers=headers)

	if not response.ok:
		return False

	tags = response.json().get("tags")

	return any(image == tag_metadata["tag"] for tag_metadata in tags)


def is_image_in_registry(image: str, group: str, settings: dict[str, str]) -> bool:
	headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
	auth = (settings["docker_registry_username"], settings["docker_registry_password"])
	namespace = (
		f"{settings['docker_registry_namespace']}/{settings['domain']}"
		if settings["docker_registry_namespace"]
		else settings["domain"]
	)
	registry = settings["docker_registry_url"]

	if registry == "registry.digitalocean.com":
		return query_digitalocean_registry(image, group, settings)

	url = f"https://{registry}/v2/{namespace}/{group}/tags/list"

	response = requests.get(url, auth=auth, headers=headers)

	if not response.ok:
		return False

	image_tags = response.json().get("tags")
	return image in image_tags


def on_doctype_update():
	if frappe.flags.in_install:
		return
	# Ignoring filesorts
	# https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html#order-by-index-use
	frappe.db.add_index("Deploy Candidate Build", ["team", "group", "creation"])
