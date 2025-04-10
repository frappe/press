# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
# We currently don't take build steps into account.
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import tarfile
import tempfile
import typing
from datetime import datetime, timedelta
from enum import Enum
from functools import cached_property

import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime as now
from frappe.utils import rounded
from tenacity import retry, stop_after_attempt, wait_fixed

from press.agent import Agent
from press.press.doctype.deploy_candidate.deploy_notifications import (
	create_build_failed_notification,
)
from press.press.doctype.deploy_candidate.docker_output_parsers import (
	DockerBuildOutputParser,
	UploadStepUpdater,
)
from press.press.doctype.deploy_candidate.utils import (
	get_build_server,
	get_package_manager_files,
	load_pyproject,
)
from press.press.doctype.deploy_candidate.validations import PreBuildValidations
from press.utils import get_current_team, log_error
from press.utils.jobs import get_background_jobs, stop_background_job

if typing.TYPE_CHECKING:
	from rq.job import Job

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_app.deploy_candidate_app import (
		DeployCandidateApp,
	)

# build_duration, pending_duration are Time fields, >= 1 day is invalid
MAX_DURATION = timedelta(hours=23, minutes=59, seconds=59)


class Status(Enum):
	FAILURE = "Failure"
	SUCCESS = "Success"
	PENDING = "Pending"
	RUNNING = "Running"
	SCHEDULED = "Scheduled"
	PREPARING = "Preparing"

	@classmethod
	def terminal(cls):
		return [cls.FAILURE.value, cls.SUCCESS.value]

	@classmethod
	def intermediate(cls):
		return [cls.PENDING.value, cls.RUNNING.value, cls.SCHEDULED.value, cls.PREPARING.value]


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
		docker_image_id: DF.Data | None
		error_key: DF.Data | None
		manually_failed: DF.Check
		no_build: DF.Check
		no_cache: DF.Check
		no_push: DF.Check
		pending_duration: DF.Time | None
		pending_end: DF.Datetime | None
		pending_start: DF.Datetime | None
		retry_count: DF.Int
		status: DF.Literal["Pending", "Preparing", "Running", "Success", "Failure"]
		user_addressable_failure: DF.Check
	# end: auto-generated types

	@cached_property
	def candidate(self) -> DeployCandidate:
		return frappe.get_doc("Deploy Candidate", self.deploy_candidate)

	def set_status(self, status: Status, timestamp_field: str | None = None, commit: bool = True):
		self.status = status.value

		if self.status == Status.FAILURE.value:
			self._fail_last_running_step()

		if timestamp_field and hasattr(self, timestamp_field):
			setattr(self, timestamp_field, now())

		self.db_update()

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

	def _generate_dockerfile(self):
		dockerfile = os.path.join(self.build_directory, "Dockerfile")
		with open(dockerfile, "w") as f:
			dockerfile_template = "press/docker/Dockerfile"

			for d in self.candidate.dependencies:
				if d.dependency == "BENCH_VERSION" and d.version == "5.2.1":
					dockerfile_template = "press/docker/Dockerfile_Bench_5_2_1"

			content = frappe.render_template(dockerfile_template, {"doc": self.candidate}, is_path=True)
			f.write(content)
			return content

	def _generate_redis_cache_config(self):
		redis_cache_conf = os.path.join(self.build_directory, "config", "redis-cache.conf")
		with open(redis_cache_conf, "w") as f:
			redis_cache_conf_template = "press/docker/config/redis-cache.conf"
			content = frappe.render_template(redis_cache_conf_template, {"doc": self.candidate}, is_path=True)
			f.write(content)

	def _generate_redis_queue_config(self):
		redis_queue_conf = os.path.join(self.build_directory, "config", "redis-queue.conf")
		with open(redis_queue_conf, "w") as f:
			redis_queue_conf_template = "press/docker/config/redis-queue.conf"
			content = frappe.render_template(redis_queue_conf_template, {"doc": self.candidate}, is_path=True)
			f.write(content)

	def _generate_supervisor_config(self):
		supervisor_conf = os.path.join(self.build_directory, "config", "supervisor.conf")
		with open(supervisor_conf, "w") as f:
			supervisor_conf_template = "press/docker/config/supervisor.conf"
			content = frappe.render_template(supervisor_conf_template, {"doc": self.candidate}, is_path=True)
			f.write(content)

	def _generate_apps_txt(self):
		apps_txt = os.path.join(self.build_directory, "apps.txt")
		with open(apps_txt, "w") as f:
			content = "\n".join([app.app_name for app in self.candidate.apps])
			f.write(content)

	def _copy_config_files(self):
		for target in ["common_site_config.json", "supervisord.conf", ".vimrc"]:
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

		PreBuildValidations(self.candidate, pmf).validate()

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

		if job_data.get("build_failure"):
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

	def handle_build_failure(
		self,
		exc: Exception | None = None,
		job: "AgentJob | None" = None,
	) -> None:
		self._flush_output_parsers()
		self.set_status(Status.FAILURE)
		self._set_build_duration()
		# self.candidate._set_status_failure()
		should_retry = self.should_build_retry(exc=exc, job=job)

		if not should_retry:
			self.candidate._fail_site_group_deploy_if_exists()

		# Do not send a notification if the build is being retried.
		if not should_retry and create_build_failed_notification(self, exc):
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
		self.retry_count += 1
		minutes = min(5**self.retry_count, 125)
		scheduled_time = now() + timedelta(minutes=minutes)
		self.candidate.schedule_build_and_deploy(
			run_now=False,
			scheduled_time=scheduled_time,
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

		self.db_update()

	def _set_build_duration(self):
		self.build_end = now()
		if not isinstance(self.build_start, datetime):
			return

		self.build_duration = min(
			self.build_end - self.build_start,
			MAX_DURATION,
		)

		self.db_update()

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

		if self.candidate.status == "Success" and request_data.get("deploy_after_build"):
			self.candidate.create_deploy()

	def _prepare_build_directory(self):
		build_directory = frappe.get_value("Press Settings", None, "build_directory")
		if not os.path.exists(build_directory):
			os.mkdir(build_directory)

		group_directory = os.path.join(build_directory, self.candidate.group)
		if not os.path.exists(group_directory):
			os.mkdir(group_directory)

		self.build_directory = os.path.join(build_directory, self.candidate.group, self.name)
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
		self.candidate.save(ignore_permissions=True)

		# Set props used when generating the Dockerfile
		self.candidate._set_additional_packages()
		self.candidate._set_container_mounts()

		# Dockerfile generation
		dockerfile = self._generate_dockerfile()
		self.add_build_steps(dockerfile)
		self.add_post_build_steps()

		self._copy_config_files()
		self._generate_redis_cache_config()
		self._generate_redis_queue_config()
		self._generate_supervisor_config()
		self._generate_apps_txt()
		self.candidate.generate_ssh_keys()

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
		settings = self.candidate._fetch_registry_settings()

		Agent(self.build_server).run_build(
			{
				"filename": context_filename,
				"image_repository": self.candidate.docker_image_repository,
				"image_tag": self.candidate.docker_image_tag,
				"registry": {
					"url": settings.docker_registry_url,
					"username": settings.docker_registry_username,
					"password": settings.docker_registry_password,
				},
				"no_cache": self.no_cache,
				"no_push": self.no_push,
				# Next few values are not used by agent but are
				# read in `process_run_build`
				"deploy_candidate_build": self.name,
				"deploy_after_build": self.deploy_after_build,
			}
		)

		self.set_status(Status.RUNNING)
		# self.candidate._set_status_running()

	def _start_build(self):
		self.candidate._update_docker_image_metadata()
		if self.no_build:
			return

		self._run_agent_jobs()

	def _build(self):
		self.set_status(Status.PREPARING, "build_start")
		self._set_pending_duration()
		# self.candidate._set_status_preparing()
		self._set_output_parsers()

		try:
			self._prepare_build()
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

	def set_build_server(self):
		if not self.build_server:
			self.build_server = get_build_server(self.candidate.group)

		if self.build_server or self.no_build:
			return

		throw_no_build_server()

	def validate_status(self):
		if self.candidate.status in ["Draft", "Success", "Failure", "Scheduled"]:
			return True

		frappe.msgprint(
			f"Build is in <b>{self.candidate.status}</b> state. "
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
			self.doctype, self.name, "_build", queue=queue, timeout=2400, enqueue_after_commit=True
		)

		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	def after_insert(self):
		self.pre_build()

	def autoname(self):
		candidate_name = self.candidate.name[7:]
		series = f"build-{candidate_name}-.######"
		self.name = make_autoname(series)

	def _stop_and_fail(self):
		for job in get_background_jobs(self.doctype, self.name, status="started"):
			if is_build_job(job):
				stop_background_job(job)

		self.set_status(Status.FAILURE)
		self._set_build_duration()
		# self.candidate._set_status_failure()

	@frappe.whitelist()
	def cleanup_build_directory(self):
		if not self.build_directory:
			return

		if os.path.exists(self.build_directory):
			shutil.rmtree(self.build_directory)

		self.build_directory = None
		self.save()

	@frappe.whitelist()
	def stop_and_fail(self):
		if self.status in Status.terminal():
			return dict(
				error=True,
				message=f"Cannot stop and fail if status one of [{', '.join(Status.terminal())}]",
			)
		self.manually_failed = True
		self._stop_and_fail()
		return dict(error=False, message="Failed successfully")


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


def throw_no_build_server():
	frappe.throw(
		"Server not found to run builds. "
		"Please set <b>Build Server</b> under <b>Press Settings > Docker > Docker Build</b>."
	)
