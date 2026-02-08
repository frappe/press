# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
# We currently don't take build steps into account.
from __future__ import annotations

import contextlib
import glob
import json
import os
import re
import shutil
import tarfile
import tempfile
import typing
import warnings
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
from frappe.query_builder.custom import GROUP_CONCAT
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
	DockerBuildOutputParser,
	UploadStepUpdater,
)
from press.press.doctype.deploy_candidate.utils import (
	BuildWarning,
	get_arm_build_server_with_least_active_builds,
	get_build_server,
	get_intel_build_server_with_least_active_builds,
	get_package_manager_files,
	is_suspended,
	load_pyproject,
)
from press.press.doctype.deploy_candidate.validations import PreBuildValidations
from press.utils import get_current_team, log_error
from press.utils.jobs import get_background_jobs, stop_background_job
from press.utils.webhook import create_webhook_event

if typing.TYPE_CHECKING:
	from warnings import WarningMessage

	from rq.job import Job

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_app.deploy_candidate_app import (
		DeployCandidateApp,
	)
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


class ConfigFileTemplate(Enum):
	REDIS_CACHE = "press/docker/config/redis-cache.conf"
	REDIS_QUEUE = "press/docker/config/redis-queue.conf"
	SUPERVISOR = "press/docker/config/supervisor.conf"


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
	"package": "Package",
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
	("package", "context"): "Build Context",
	("upload", "context"): "Build Context",
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
) -> tuple[str, str]:
	stage = STAGE_SLUG_MAP.get(stage_slug, stage_slug)
	step = step_slug
	if stage_slug == "clone" or stage_slug == "apps":
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

	@staticmethod
	def get_list_query(query, filters=None, **list_args):
		DeployCandidate, DeployCandidateBuild, DeployCandidateApp = (
			frappe.qb.DocType("Deploy Candidate"),
			frappe.qb.DocType("Deploy Candidate Build"),
			frappe.qb.DocType("Deploy Candidate App"),
		)
		query = (
			query.left_join(DeployCandidate)
			.on(DeployCandidateBuild.deploy_candidate == DeployCandidate.name)
			.left_join(DeployCandidateApp)
			.on(DeployCandidateApp.parent == DeployCandidate.name)
			.select(
				DeployCandidateBuild.name,
				DeployCandidateBuild.creation,
				DeployCandidateBuild.status,
				DeployCandidateBuild.build_duration,
				DeployCandidateBuild.owner,
				GROUP_CONCAT(DeployCandidateApp.app).as_("apps"),
			)
			.groupby(DeployCandidateBuild.name)
		)
		results = query.run(as_dict=True)

		for deploy in results:
			if not isinstance(deploy["apps"], list):
				deploy["apps"] = [deploy["apps"]]

		return results

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

	def _generate_dockerfile(self):
		dockerfile = os.path.join(self.build_directory, "Dockerfile")
		with open(dockerfile, "w") as f:
			dockerfile_template = "press/docker/Dockerfile"
			is_distutils_supported = True
			requires_version_based_get_pip = False

			for d in self.candidate.dependencies:
				if d.dependency == "PYTHON_VERSION":
					is_distutils_supported = self.check_distutils_support(d.version)
					requires_version_based_get_pip = self.check_get_pip_url_support(d.version)

				if d.dependency == "BENCH_VERSION" and d.version == "5.2.1":
					dockerfile_template = "press/docker/Dockerfile_Bench_5_2_1"

			team_deploying = frappe.db.get_value("Release Group", self.group, "team")
			content = frappe.render_template(
				dockerfile_template,
				{
					"doc": self.candidate,
					"remove_distutils": not is_distutils_supported,
					"requires_version_based_get_pip": requires_version_based_get_pip,
					"is_arm_build": self.platform == "arm64",
					"use_asset_store": int(
						frappe.db.get_single_value("Press Settings", "use_asset_store")
						or team_deploying == "team@erpnext.com"
					),
					"upload_assets": int(
						frappe.db.get_value("Release Group", self.group, "public")
						or team_deploying == "team@erpnext.com"
					),
					"site_url": frappe.utils.get_url(),
				},
				is_path=True,
			)
			f.write(content)
			return content

	def _generate_config_from_template(self, template: ConfigFileTemplate):
		_, template_conf_name = os.path.split(template.value)
		conf_file = os.path.join(self.build_directory, "config", template_conf_name)

		with open(conf_file, "w") as f:
			content = frappe.render_template(
				template.value, {"doc": self.candidate, "platform": self.platform}, is_path=True
			)
			f.write(content)

	def _generate_apps_txt(self):
		apps_txt = os.path.join(self.build_directory, "apps.txt")
		with open(apps_txt, "w") as f:
			content = "\n".join([app.app_name for app in self.candidate.apps])
			f.write(content)

	def _copy_config_files(self):
		for target in ["common_site_config.json", "supervisord.conf", ".vimrc", "get_cached_app.py"]:
			shutil.copy(os.path.join(frappe.get_app_path("press", "docker"), target), self.build_directory)

		for target in ["config", "redis"]:
			shutil.copytree(
				os.path.join(frappe.get_app_path("press", "docker"), target),
				os.path.join(self.build_directory, target),
				symlinks=True,
			)

	def _get_app_name(self, app):
		"""Retrieves `name` attribute of app - equivalent to distribution name
		of python package. Fetches from pyproject.toml, setup.cfg or setup.py
		whichever defines it in that order.
		"""
		app_name = None
		apps_path = os.path.join(self.build_directory, "apps")

		config_py_path = os.path.join(apps_path, app, "setup.cfg")
		setup_py_path = os.path.join(apps_path, app, "setup.py")

		app_name = self._get_app_pyproject(app).get("project", {}).get("name")

		if not app_name and os.path.exists(config_py_path):
			from setuptools.config import read_configuration

			config = read_configuration(config_py_path)
			app_name = config.get("metadata", {}).get("name")

		if not app_name and os.path.exists(setup_py_path):
			# retrieve app name from setup.py as fallback
			with open(setup_py_path, "rb") as f:
				contents = f.read().decode("utf-8")
				search = re.search(r'name\s*=\s*[\'"](.*)[\'"]', contents)

			if search:
				app_name = search[1]

		if app_name and app != app_name:
			return app_name

		return app

	def _get_app_pyproject(self, app):
		apps_path = os.path.join(self.build_directory, "apps")
		pyproject_path = os.path.join(apps_path, app, "pyproject.toml")
		if not os.path.exists(pyproject_path):
			return {}

		return load_pyproject(app, pyproject_path)

	def _clone_release_and_update_step(self, release, step):
		step.cached = False
		step.status = "Running"
		start_time = now()
		self.save(ignore_version=True)

		release: AppRelease = frappe.get_doc("App Release", release, for_update=True)
		release._clone(force=True)

		frappe.db.commit()  # Release lock taken for app clone

		step.duration = get_duration(start_time)
		step.output = release.output
		step.status = "Success"
		return release.clone_directory

	def _clone_app(self, app: DeployCandidateApp):
		step = self.get_step("clone", app.app)
		source, cloned = frappe.get_value("App Release", app.release, ["clone_directory", "cloned"])

		step.command = f"git clone {app.app}"

		if cloned and os.path.exists(source):
			step.cached = True
			step.status = "Success"
		else:
			source = self._clone_release_and_update_step(app.release, step)

		target = os.path.join(self.build_directory, "apps", app.app)
		shutil.copytree(source, target, symlinks=True)

		if app.pullable_release:
			source = frappe.get_value("App Release", app.pullable_release, "clone_directory")
			target = os.path.join(self.build_directory, "app_updates", app.app)
			# don't know why
			shutil.copytree(source, target, symlinks=True)

		return target

	def _clone_repositories(self):
		repo_path_map = {}

		for app in self.candidate.apps:
			repo_path_map[app.app] = self._clone_app(app)
			app.app_name = self._get_app_name(app.app)

		return repo_path_map

	def _run_pre_build_validation(self, pmf):
		step = self.get_step("validate", "pre-build")
		step.status = "Running"
		start_time = now()
		self.save(ignore_version=True)

		try:
			PreBuildValidations(self.candidate, pmf).validate()
		except Exception as e:
			step.output = str(e)
			# We need to raise to get traceback in `deploy notifications`
			raise e

		step.duration = get_duration(start_time)
		step.output = "Pre-Build validations passed"
		step.status = "Success"
		self.save(ignore_version=True)

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

	def add_pre_build_steps(self):
		app_titles = {a.app: a.title for a in self.candidate.apps}

		# Clone app slugs
		slugs: list[tuple[str, str]] = [("clone", app.app) for app in self.candidate.apps]

		slugs.extend(
			[
				# Pre-build validation slug
				("validate", "pre-build"),
				# Build slugs
				("package", "context"),
				("upload", "context"),
			]
		)

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

			step = dict(
				status="Pending",
				stage_slug=stage_slug,
				step_slug=step_slug,
				stage=stage,
				step=step,
			)
			self.append("build_steps", step)

		self.save()

	def _flush_output_parsers(self, commit=False):
		if self.build_output_parser:
			self.build_output_parser.flush_output(commit)

		if self.upload_step_updater:
			self.upload_step_updater.flush_output(commit)

	def _set_output_parsers(self):
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

	def _process_run_build(
		self,
		job: "AgentJob",
		request_data: dict,
		response_data: dict | None,
	):
		job_data = json.loads(job.data or "{}")
		output_data = json.loads(job_data.get("output", "{}"))

		"""
		Due to how agent - press communication takes place, every time an
		output is published all of it has to be re-parsed from the start.

		This is due to a method of streaming agent output to press not
		existing.
		"""
		self._set_output_parsers()
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

	def _prepare_build_directory(self):
		build_directory = frappe.get_value("Press Settings", None, "build_directory")
		if not os.path.exists(build_directory):
			os.mkdir(build_directory)

		group_directory = os.path.join(build_directory, self.group)
		if not os.path.exists(group_directory):
			os.mkdir(group_directory)

		self.build_directory = os.path.join(build_directory, self.group, self.name)
		if os.path.exists(self.build_directory):
			shutil.rmtree(self.build_directory)

		os.mkdir(self.build_directory)

	def _prepare_build_context(self):
		repo_path_map = self._clone_repositories()
		pmf = get_package_manager_files(repo_path_map)
		self._run_pre_build_validation(pmf)

		"""
		Due to dependencies mentioned in an apps pyproject.toml
		file, _update_packages() needs to run after the repos
		have been cloned.
		"""
		self.candidate._update_packages(pmf)

		# Set props used when generating the Dockerfile
		self.candidate._set_additional_packages()
		self.candidate._set_container_mounts()

		# Dockerfile generation
		dockerfile = self._generate_dockerfile()
		self.add_build_steps(dockerfile)
		self.add_post_build_steps()

		self._copy_config_files()
		for config_template in [
			ConfigFileTemplate.REDIS_CACHE,
			ConfigFileTemplate.REDIS_QUEUE,
			ConfigFileTemplate.SUPERVISOR,
		]:
			self._generate_config_from_template(config_template)

		self._generate_apps_txt()
		self.candidate.generate_ssh_keys(self.build_directory)

	def _prepare_build(self):
		if not self.no_cache:
			self.candidate._update_app_releases()

		if not self.no_cache:
			self.candidate._set_app_cached_flags()

		self._prepare_build_directory()
		self._prepare_build_context()

	def get_step(self, stage_slug: str, step_slug: str) -> "DeployCandidateBuildStep | None":
		return find(
			self.build_steps,
			lambda x: x.stage_slug == stage_slug and x.step_slug == step_slug,
		)

	def _upload_build_context(self, context_filepath: str, build_server: str):
		step = self.get_step("upload", "context") or frappe._dict()
		step.status = "Running"
		start_time = now()
		self.save(ignore_version=True)

		try:
			upload_filename = self.upload_build_context_for_docker_build(
				context_filepath,
				build_server,
			)
		except Exception:
			step.status = "Failure"
			raise

		step.status = "Success"
		step.duration = get_duration(start_time)
		self.save(ignore_version=True)
		return upload_filename

	def _package_build_context(self):
		step = self.get_step("package", "context") or frappe._dict()
		step.status = "Running"
		start_time = now()
		self.save(ignore_version=True)

		def fix_content_permission(tarinfo):
			tarinfo.uid = 1000
			tarinfo.gid = 1000
			return tarinfo

		tmp_file_path = tempfile.mkstemp(suffix=".tar.gz")[1]
		with tarfile.open(tmp_file_path, "w:gz", compresslevel=5) as tar:
			if frappe.conf.developer_mode:
				tar.add(self.build_directory, arcname=".", filter=fix_content_permission)
			else:
				tar.add(self.build_directory, arcname=".")

		step.status = "Success"
		step.duration = get_duration(start_time)
		self.save(ignore_version=True)

		return tmp_file_path

	def _package_and_upload_context(self):
		context_filepath = self._package_build_context()
		context_filename = self._upload_build_context(
			context_filepath,
			self.build_server,
		)
		os.remove(context_filepath)
		return context_filename

	def _run_agent_jobs(self):
		context_filename = self._package_and_upload_context()
		settings = self._fetch_registry_settings()

		build_parameters = {
			"filename": context_filename,
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
		}
		if self.platform == "arm64":
			build_parameters.update({"platform": self.platform})

		Agent(self.build_server).run_build(build_parameters)

		self.set_status(Status.RUNNING)

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

	def _start_build(self):
		self._update_docker_image_metadata()
		self._run_agent_jobs()

	def _build(self):
		self._set_pending_duration()
		self.set_status(
			Status.PREPARING,
			timestamp_field="build_start",
			commit=True,
		)
		self._set_output_parsers()

		# https://docs.python.org/3/library/warnings.html#testing-warnings
		with warnings.catch_warnings(record=True) as caught_warnings:
			warnings.simplefilter("always", BuildWarning)  # capture everything

			try:
				self._prepare_build()
			except Exception as exc:
				self.handle_build_failure(exc)
				return

			for warning in caught_warnings:
				self.handle_build_warning(
					title="Pre Build Validation Warning",
					warning=warning,
				)

		try:
			self._start_build()
		except Exception as exc:
			self.handle_build_failure(exc)

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
			get_current_team(True),
		)

		frappe.set_user(frappe.get_value("Team", team.name, "user"))
		queue = "default" if frappe.conf.developer_mode else "build"

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_build",
			queue=queue,
			timeout=2400,
			enqueue_after_commit=True,
		)

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
		self.manually_failed = True
		for job in get_background_jobs(self.doctype, self.name, status="started"):
			if is_build_job(job):
				stop_background_job(job)

		self.set_status(Status.FAILURE)
		self._set_build_duration()

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

	if agent_job.status != "Running":
		return False

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
		dcb.manually_failed = True
		dcb._stop_and_fail()
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
