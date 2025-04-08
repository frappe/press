# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
# We currently don't take build steps into account.
from __future__ import annotations

import contextlib
import json
import os
import shutil
import tarfile
import tempfile
import typing

import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.utils import now_datetime as now
from frappe.utils import rounded

from press.agent import Agent
from press.press.doctype.deploy_candidate.docker_output_parsers import (
	DockerBuildOutputParser,
	UploadStepUpdater,
)
from press.press.doctype.deploy_candidate.utils import get_package_manager_files
from press.press.doctype.deploy_candidate.validations import PreBuildValidations
from press.utils import get_current_team

if typing.TYPE_CHECKING:
	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_app.deploy_candidate_app import (
		DeployCandidateApp,
	)

from functools import cached_property

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
	step_name: Literal["build", "push"],
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

		build_error: DF.Code | None
		build_output: DF.Code | None
		build_steps: DF.Table[DeployCandidateBuildStep]
		deploy_candidate: DF.Link
		no_build: DF.Check
		no_cache: DF.Check
		no_push: DF.Check
	# end: auto-generated types

	@cached_property
	def candidate(self) -> DeployCandidate:
		return frappe.get_doc("Deploy Candidate", self.deploy_candidate)

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

		target = os.path.join(self.candidate.build_directory, "apps", app.app)
		shutil.copytree(source, target, symlinks=True)

		if app.pullable_release:
			source = frappe.get_value("App Release", app.pullable_release, "clone_directory")
			target = os.path.join(self.candidate.build_directory, "app_updates", app.app)
			# don't know why
			shutil.copytree(source, target, symlinks=True)

		return target

	def _clone_repositories(self):
		repo_path_map = {}

		for app in self.candidate.apps:
			repo_path_map[app.app] = self._clone_app(app)
			app.app_name = self.candidate._get_app_name(app.app)

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

	def add_pre_build_steps(self):
		"""
		This function just adds build steps that occur before
		a docker build, rest of the steps are updated after the
		Dockerfile is generated in:
		- `_update_build_steps`
		- `_update_post_build_steps`
		"""
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

	def add_build_steps(self, dockerfile: str):
		app_titles = {a.app: a.title for a in self.candidate.apps}

		checkpoints = self.candidate._get_dockerfile_checkpoints(dockerfile)
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

	def _set_output_parsers(self):
		self.build_output_parser = DockerBuildOutputParser(self)
		self.upload_step_updater = UploadStepUpdater(self)

	def correct_upload_step_status(self):
		if not (usu := self.upload_step_updater) or not usu.upload_step:
			return

		if self.candidate.status == "Success" and usu.upload_step.status == "Running":
			self.upload_step_updater.end("Success")

		elif self.candidate.status == "Failure" and usu.upload_step.status not in [
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
			# self.handle_build_failure(exc=None, job=job)
			...
		else:
			self.candidate._update_status_from_remote_build_job(job)

		# Fallback case cause upload step can be left hanging
		self.correct_upload_step_status()

		if self.candidate.status == "Success" and request_data.get("deploy_after_build"):
			self.candidate.create_deploy()

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
		dockerfile = self.candidate._generate_dockerfile()
		self.add_build_steps(dockerfile)

		self.candidate._copy_config_files()
		self.candidate._generate_redis_cache_config()
		self.candidate._generate_redis_queue_config()
		self.candidate._generate_supervisor_config()
		self.candidate._generate_apps_txt()
		self.candidate.generate_ssh_keys()

	def _prepare_build(self):
		if not self.no_cache:
			self.candidate._update_app_releases()

		if not self.no_cache:
			self.candidate._set_app_cached_flags()

		self.candidate._prepare_build_directory()
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
			upload_filename = self.candidate.upload_build_context_for_docker_build(
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
				tar.add(self.candidate.build_directory, arcname=".", filter=fix_content_permission)
			else:
				tar.add(self.candidate.build_directory, arcname=".")

		step.status = "Success"
		step.duration = get_duration(start_time)
		self.save(ignore_version=True)

		return tmp_file_path

	def _package_and_upload_context(self):
		context_filepath = self._package_build_context()
		context_filename = self._upload_build_context(
			context_filepath,
			self.candidate.build_server,
		)
		os.remove(context_filepath)
		return context_filename

	def _run_agent_jobs(self, deploy_after_build):
		context_filename = self._package_and_upload_context()
		settings = self.candidate._fetch_registry_settings()

		Agent(self.candidate.build_server).run_build(
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
				"deploy_after_build": deploy_after_build,
			}
		)
		self.last_updated = now()
		self.candidate._set_status_running()

	def _start_build(self, deploy_after_build: bool = False):
		self.candidate._update_docker_image_metadata()  # we just assing a docker image tag

		if self.no_build:
			return

		self._run_agent_jobs(deploy_after_build)

	def _build(self):
		self._prepare_build()
		self._start_build()

	def reset_build_steps(self):
		self.build_steps.clear()

	def pre_build(self):
		self.reset_build_steps()
		self.add_pre_build_steps()

		# VALIDATE STATUS
		self.candidate.set_build_server(self.no_build)
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
		# queue = "default" if frappe.conf.developer_mode else "build"

		# ENQUEUE!
		self._build()
		# frappe.enqueue(self._build, queue=queue, timeout=2400, enqueue_after_commit=True)

		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	def after_insert(self):
		self.pre_build()
