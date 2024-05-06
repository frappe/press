# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import typing
from datetime import datetime, timedelta
from subprocess import Popen
from typing import Any, List, Literal, Optional, Tuple, Generator

import docker
import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime as now
from press.agent import Agent
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.app_release.app_release import (
	AppReleasePair,
	get_changed_files_between_hashes,
)
from press.press.doctype.deploy_candidate.deploy_notifications import (
	create_build_failed_notification,
)
from press.press.doctype.deploy_candidate.utils import (
	load_pyproject,
	get_package_manager_files,
	PackageManagerFiles,
)
from press.press.doctype.deploy_candidate.validations import PreBuildValidations
from press.press.doctype.deploy_candidate.docker_output_parsers import (
	DockerBuildOutputParser,
	UploadStepUpdater,
)
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.utils import get_current_team, log_error, reconnect_on_failure

if typing.TYPE_CHECKING:

	from press.press.doctype.agent_job.agent_job import AgentJob
	from press.press.doctype.app_release.app_release import AppRelease


class DeployCandidate(Document):
	# This is altered in CI
	base_build_command: str = "docker buildx build --platform linux/amd64"

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.deploy_candidate_app.deploy_candidate_app import (
			DeployCandidateApp,
		)
		from press.press.doctype.deploy_candidate_build_step.deploy_candidate_build_step import (
			DeployCandidateBuildStep,
		)
		from press.press.doctype.deploy_candidate_dependency.deploy_candidate_dependency import (
			DeployCandidateDependency,
		)
		from press.press.doctype.deploy_candidate_package.deploy_candidate_package import (
			DeployCandidatePackage,
		)
		from press.press.doctype.deploy_candidate_variable.deploy_candidate_variable import (
			DeployCandidateVariable,
		)

		apps: DF.Table[DeployCandidateApp]
		build_directory: DF.Data | None
		build_duration: DF.Time | None
		build_end: DF.Datetime | None
		build_error: DF.Code | None
		build_output: DF.Code | None
		build_start: DF.Datetime | None
		build_steps: DF.Table[DeployCandidateBuildStep]
		compress_app_cache: DF.Check
		dependencies: DF.Table[DeployCandidateDependency]
		docker_image: DF.Data | None
		docker_image_id: DF.Data | None
		docker_image_repository: DF.Data | None
		docker_image_tag: DF.Data | None
		docker_remote_builder_server: DF.Link | None
		environment_variables: DF.Table[DeployCandidateVariable]
		group: DF.Link
		gunicorn_threads_per_worker: DF.Int
		is_docker_remote_builder_used: DF.Check
		is_redisearch_enabled: DF.Check
		is_single_container: DF.Check
		is_ssh_enabled: DF.Check
		last_updated: DF.Datetime | None
		merge_all_rq_queues: DF.Check
		merge_default_and_short_rq_queues: DF.Check
		packages: DF.Table[DeployCandidatePackage]
		scheduled_time: DF.Datetime | None
		status: DF.Literal[
			"Draft", "Scheduled", "Pending", "Preparing", "Running", "Success", "Failure"
		]
		team: DF.Link
		use_app_cache: DF.Check
		use_rq_workerpool: DF.Check
		user_addressable_failure: DF.Check
		user_certificate: DF.Code | None
		user_private_key: DF.Code | None
		user_public_key: DF.Code | None
		# end: auto-generated types

		# Used for local builds, for remote builds instances
		# are created when handling job update
		build_output_parser: Optional[DockerBuildOutputParser]
		upload_step_updater: Optional[UploadStepUpdater]

	dashboard_fields = [
		"name",
		"status",
		"creation",
		"deployed",
		"build_steps",
		"build_start",
		"build_end",
		"build_duration",
		"build_error",
		"apps",
		"group",
	]

	@staticmethod
	def get_list_query(query):
		results = query.run(as_dict=True)
		names = [r.name for r in results if r.status and r.status != "Success"]
		notifications = frappe.get_all(
			"Press Notification",
			fields=["name", "document_name"],
			filters={
				"document_type": "Deploy Candidate",
				"document_name": ["in", names],
				"class": "Error",
				"is_actionable": True,
				"is_addressed": False,
			},
		)
		notification_map = {n.document_name: n.name for n in notifications}
		for result in results:
			if name := result.get("name"):
				result.addressable_notification = notification_map.get(name)

		return results

	def get_doc(self, doc):
		doc.jobs = []
		deploys = frappe.get_all("Deploy", {"candidate": self.name}, limit=1)
		if deploys:
			deploy = frappe.get_doc("Deploy", deploys[0].name)
			for bench in deploy.benches:
				if not bench.bench:
					continue
				job = frappe.get_all(
					"Agent Job",
					["name", "status", "end", "duration", "bench"],
					{"bench": bench.bench, "job_type": "New Bench"},
					limit=1,
				) or [{}]
				doc.jobs.append(job[0])

	def autoname(self):
		group = self.group[6:]
		series = f"deploy-{group}-.######"
		self.name = make_autoname(series)

	def before_insert(self):
		if self.status == "Draft":
			self.build_duration = 0

	def on_trash(self):
		frappe.db.delete(
			"Press Notification",
			{"document_type": self.doctype, "document_name": self.name},
		)

	def get_unpublished_marketplace_releases(self) -> List[str]:
		rg: ReleaseGroup = frappe.get_doc("Release Group", self.group)
		marketplace_app_sources = rg.get_marketplace_app_sources()

		if not marketplace_app_sources:
			return []

		# Marketplace App Releases in this deploy candidate
		dc_app_releases = frappe.get_all(
			"Deploy Candidate App",
			filters={"parent": self.name, "source": ("in", marketplace_app_sources)},
			pluck="release",
		)

		# Unapproved app releases for marketplace apps
		unpublished_releases = frappe.get_all(
			"App Release",
			filters={"name": ("in", dc_app_releases), "status": ("!=", "Approved")},
			pluck="name",
		)

		return unpublished_releases

	def pre_build(self, method, **kwargs):
		if not self.validate_status():
			return

		self.status = "Pending"
		self.set_remote_build_flags()
		self.reset_build_state()
		self.add_pre_build_steps()
		self.save()
		user, session_data, team, = (
			frappe.session.user,
			frappe.session.data,
			get_current_team(True),
		)
		frappe.set_user(frappe.get_value("Team", team.name, "user"))
		queue = "default" if frappe.conf.developer_mode else "build"

		frappe.enqueue_doc(
			self.doctype,
			self.name,
			method,
			queue=queue,
			timeout=2400,
			enqueue_after_commit=True,
			**kwargs,
		)
		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	def set_remote_build_flags(self):
		if not self.docker_remote_builder_server:
			self.docker_remote_builder_server = self._get_docker_remote_builder_server()

		if not self.docker_remote_builder_server:
			return

		self.is_docker_remote_builder_used = True

	def validate_status(self):
		if self.status in ["Draft", "Success", "Failure"]:
			return True

		frappe.msgprint(
			f"Build is in <b>{self.status}</b> state. "
			"Please wait for build to succeed or fail before retrying."
		)
		return False

	@frappe.whitelist()
	def generate_build_context(self):
		self.pre_build(method="_build", no_build=True)

	@frappe.whitelist()
	def build(self):
		self.pre_build(method="_build")

	@frappe.whitelist()
	def build_without_cache(self):
		self.pre_build(method="_build", no_cache=True)

	@frappe.whitelist()
	def build_without_push(self):
		self.pre_build(method="_build", no_push=True)

	@frappe.whitelist()
	def fail_and_redeploy(self):
		if self.status == "Draft" or self.status == "Failure" or self.status == "Success":
			return

		self._set_status_failure()
		return self.redeploy()

	@frappe.whitelist()
	def redeploy(self):
		if not (dc := self.get_duplicate_dc()):
			return

		dc.build_and_deploy()
		return dc

	@frappe.whitelist()
	def schedule_build_and_deploy(self, is_running_scheduled=False):
		"""
		If Builds are suspended (Press Settings > Suspend Builds) then this
		puts the build into scheduled mode.

		Execution will be retried on scheduler tick from `run_scheduled_builds`

		To bypass this run `build_and_deploy` directly.
		"""
		if self.status == "Scheduled" and not is_running_scheduled:
			return

		if not is_suspended():
			self.build_and_deploy()
			return

		# Schedule build to be run ASAP.
		self.status = "Scheduled"
		self.scheduled_time = frappe.utils.now_datetime()
		self.save()
		frappe.db.commit()

	def build_and_deploy(self):
		self.pre_build(method="_build_and_deploy")

	def _build_and_deploy(self):
		success = self._build(deploy_after_build=True)
		if not success or self.is_docker_remote_builder_used:
			return

		self._deploy()

	def _deploy(self):
		try:
			self.create_deploy()
		except Exception:
			log_error(
				"Deploy Creation Error",
				candidate=self.name,
				reference_doctype="Deploy Candidate",
				reference_name=self.name,
			)

	def _build(
		self,
		no_cache: bool = False,
		no_push: bool = False,
		no_build: bool = False,
		# Used for docker remote build
		deploy_after_build: bool = False,
	):
		self.is_single_container = True
		self.is_ssh_enabled = True

		self._set_status_preparing()
		self._set_output_parsers()
		try:
			self._prepare_build(no_cache, no_push)
			self._start_build(
				no_cache,
				no_push,
				no_build,
				deploy_after_build,
			)
		except Exception as exc:
			self._handle_build_exception(exc)
			return False

		return self.status == "Success"

	def _handle_build_exception(self, exc: Exception) -> None:
		self._flush_output_parsers()
		self._set_status_failure()

		if create_build_failed_notification(self, exc):
			self.user_addressable_failure = True
			self.save(ignore_version=True, ignore_permissions=True)
			frappe.db.commit()
			return

		# Log and raise error if build failure is not actionable
		log_error("Deploy Candidate Build Exception", name=self.name, doc=self)
		raise

	def _set_output_parsers(self):
		self.build_output_parser = DockerBuildOutputParser(self)
		self.upload_step_updater = UploadStepUpdater(self)

	def _flush_output_parsers(self):
		if self.build_output_parser:
			self.build_output_parser.flush_output(False)

		if self.upload_step_updater:
			self.upload_step_updater.flush_output(False)

	def _prepare_build(self, no_cache: bool = False, no_push: bool = False):
		if not no_cache:
			self._update_app_releases()

		if not no_cache:
			self._set_app_cached_flags()

		self._prepare_build_directory()
		self._prepare_build_context(no_push)

	def _start_build(
		self,
		no_cache: bool = False,
		no_push: bool = False,
		no_build: bool = False,
		deploy_after_build: bool = False,
	):
		self._update_docker_image_metadata()

		# Build runs on remote server
		if self.is_docker_remote_builder_used:
			self._run_remote_builder(
				deploy_after_build,
				no_cache,
				no_push,
				no_build,
			)
			return

		# Build Runs locally
		self._set_status_running()

		if not no_build:
			self._run_docker_build(no_cache)

		if not no_build and not no_push:
			self._push_docker_image()

		self._set_status_success()

	def _run_remote_builder(
		self,
		deploy_after_build: bool,
		no_cache: bool,
		no_push: bool,
		no_build: bool,
	) -> None:
		if not (remote_build_server := self.docker_remote_builder_server):
			return

		context_filepath = self._package_build_context()
		context_filename = self._upload_build_context(
			context_filepath,
			remote_build_server,
		)
		os.remove(context_filepath)
		settings = self._fetch_registry_settings()

		if no_build:
			self._set_status_success()
			return

		Agent(remote_build_server).run_remote_builder(
			{
				"filename": context_filename,
				"image_repository": self.docker_image_repository,
				"image_tag": self.docker_image_tag,
				"registry": {
					"url": settings.docker_registry_url,
					"username": settings.docker_registry_username,
					"password": settings.docker_registry_password,
				},
				"no_cache": no_cache,
				"no_push": no_push,
				# Next few values are not used by agent but are
				# read in `process_run_remote_builder`
				"deploy_candidate": self.name,
				"deploy_after_build": deploy_after_build,
			}
		)
		self.last_updated = now()
		self._set_status_running()
		return

	def _package_build_context(self) -> str:
		"""Creates a tarball of the build context and returns the path to it."""
		step = self.get_step("package", "context") or frappe._dict()
		step.status = "Running"
		start = now()

		tmp_file_path = tempfile.mkstemp(suffix=".tar.gz")[1]
		with tarfile.open(tmp_file_path, "w:gz") as tar:
			tar.add(self.build_directory, arcname=".")

		step.status = "Success"
		step.duration = frappe.utils.rounded((now() - start).total_seconds(), 1)
		return tmp_file_path

	def _upload_build_context(self, context_filepath: str, remote_build_server: str):
		step = self.get_step("upload", "context") or frappe._dict()
		step.status = "Running"
		start = now()

		agent = Agent(remote_build_server)
		with open(context_filepath, "rb") as file:
			upload_filename = agent.upload_build_context_for_docker_build(file, self.name)

		if not upload_filename:
			step.status = "Failure"
			raise Exception(
				"Failed to upload build context to remote docker builder"
				+ f"\nagent response: `{agent.response.text}`",
			)
		else:
			step.status = "Success"

		step.duration = frappe.utils.rounded((now() - start).total_seconds(), 1)
		return upload_filename

	@staticmethod
	def process_run_remote_builder(job: "AgentJob", response_data: "Optional[dict]"):
		request_data = json.loads(job.request_data)
		frappe.get_doc(
			"Deploy Candidate",
			request_data["deploy_candidate"],
		)._process_run_remote_builder(job, request_data, response_data)

	def _process_run_remote_builder(
		self,
		job: "AgentJob",
		request_data: dict,
		response_data: Optional[dict],
	):
		job_data = json.loads(job.data or "{}")
		output_data = json.loads(job_data.get("output", "{}"))

		# TODO: Error Handling
		"""
		Due to how agent - press communication takes place, every time an
		output is published all of it has to be re-parsed from the start.

		This is due to a method of streaming agent output to press not
		existing.
		"""
		if output := get_remote_step_output(
			"build",
			output_data,
			response_data,
		):
			DockerBuildOutputParser(self).parse_and_update(output)

		upload_step_updater = UploadStepUpdater(self)
		if output := get_remote_step_output(
			"push",
			output_data,
			response_data,
		):
			upload_step_updater.start()
			upload_step_updater.process(output)

		self._update_status_from_remote_build_job(job, job_data)

		if job.status == "Success":
			upload_step_updater.end("Success")

		if job.status == "Success" and request_data.get("deploy_after_build"):
			self.create_deploy()

	def _update_status_from_remote_build_job(self, job: "AgentJob", job_data: dict):
		# build_failed can be None if the build has not ended
		if job_data.get("build_failed") is True:
			return self._set_status_failure()

		match job.status:
			case "Pending" | "Running":
				return self._set_status_running()
			case "Failure" | "Undelivered" | "Delivery Failure":
				return self._set_status_failure()
			case "Success":
				return self._set_status_success()
			case _:
				raise Exception("unreachable code execution")

	def _update_docker_image_metadata(self):
		settings = self._fetch_registry_settings()

		if settings.docker_registry_namespace:
			namespace = f"{settings.docker_registry_namespace}/{settings.domain}"
		else:
			namespace = f"{settings.domain}"

		self.docker_image_repository = (
			f"{settings.docker_registry_url}/{namespace}/{self.group}"
		)
		self.docker_image_tag = self.name
		self.docker_image = f"{self.docker_image_repository}:{self.docker_image_tag}"

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

	def _set_status_preparing(self):
		self.status = "Preparing"
		self.build_start = now()
		self.save()
		frappe.db.commit()

	def _set_status_running(self):
		self.status = "Running"
		self.save(ignore_version=True)
		frappe.db.commit()

	@reconnect_on_failure()
	def _set_status_failure(self):
		self.status = "Failure"
		self._fail_last_running_step()
		self._set_duration()
		self.save(ignore_version=True)
		self._update_bench_status()
		frappe.db.commit()

	def _set_status_success(self):
		self.status = "Success"
		self.build_error = None
		self._set_duration()
		self.save(ignore_version=True)
		self._update_bench_status()
		frappe.db.commit()

	def _update_bench_status(self):
		if self.status == "Failure":
			status = "Failure"
		elif self.status == "Success":
			status = "Build Successful"
		else:
			return

		bench_update = frappe.get_all(
			"Bench Update",
			{"status": "Running", "candidate": self.name},
			pluck="name",
		)
		if not bench_update:
			return

		frappe.db.set_value("Bench Update", bench_update[0], "status", status)

	def _set_duration(self):
		self.build_end = now()
		if not isinstance(self.build_start, datetime):
			return

		build_duration = self.build_end - self.build_start
		max_duration = timedelta(hours=23, minutes=59, seconds=59)

		# build_duration is a Time field, >= 1 day is invalid
		self.build_duration = min(build_duration, max_duration)

	def _fail_last_running_step(self):
		for step in self.build_steps:
			if step.status == "Failure":
				return

			if step.status == "Running":
				step.status = "Failure"
				break

	def reset_build_state(self):
		self.build_steps.clear()
		self.build_error = ""
		self.build_output = ""
		self.build_start = None
		self.build_end = None
		self.last_updated = None
		self.build_duration = None
		self.build_directory = None

	def add_pre_build_steps(self):
		"""
		This function just adds build steps that occur before
		a docker build, rest of the steps are updated after the
		Dockerfile is generated in:
		- `_update_build_steps`
		- `_update_post_build_steps`
		"""
		app_titles = {a.app: a.title for a in self.apps}
		stage_slug = "clone"
		for app in self.apps:
			step_slug = app.app
			stage, step = get_build_stage_and_step(stage_slug, step_slug, app_titles)
			step_dict = dict(
				status="Pending",
				stage_slug=stage_slug,
				step_slug=step_slug,
				stage=stage,
				step=step,
			)
			self.append("build_steps", step_dict)

		# Additional steps for remote builder since generating and uploading
		# context take time due to tar-ing and network
		remote_build_stage_slugs = []
		if self.is_docker_remote_builder_used:
			remote_build_stage_slugs = ["package", "upload"]

		for stage_slug in remote_build_stage_slugs:
			step_slug = "context"
			stage, step = get_build_stage_and_step(stage_slug, step_slug)
			step_dict = dict(
				status="Pending",
				stage_slug=stage_slug,
				step_slug=step_slug,
				stage=stage,
				step=step,
			)
			self.append("build_steps", step_dict)
		self.save()

	def _set_app_cached_flags(self) -> None:
		for app in self.apps:
			app.use_cached = bool(self.use_app_cache)

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

	@frappe.whitelist()
	def cleanup_build_directory(self):
		if self.build_directory:
			if os.path.exists(self.build_directory):
				shutil.rmtree(self.build_directory)
			self.build_directory = None
			self.save()

	def _update_app_releases(self) -> None:
		if not frappe.get_value("Release Group", self.group, "use_delta_builds"):
			return

		try:
			update = self.get_pull_update_dict()
		except Exception:
			log_error(
				title="Failed to get Pull Update Dict",
				reference_doctype="Deploy Candidate",
				reference_name=self.name,
			)
			return

		for app in self.apps:
			if app.app not in update:
				continue

			release_pair = update[app.app]

			# Previously deployed release used for get-app
			app.hash = release_pair["old"]["hash"]
			app.release = release_pair["old"]["name"]

			# New release to be pulled after get-app
			app.pullable_hash = release_pair["new"]["hash"]
			app.pullable_release = release_pair["new"]["name"]

	def _prepare_build_context(self, no_push: bool):
		repo_path_map = self._clone_repos()
		pmf = get_package_manager_files(repo_path_map)

		"""
		Errors thrown here will be caught by a function up the
		stack, since they should be from expected invalids, they
		should also be user addressable.
		"""
		PreBuildValidations(self, pmf).validate()

		"""
		Due to dependencies mentioned in an apps pyproject.toml
		file, _update_packages() needs to run after the repos
		have been cloned.
		"""
		self._update_packages(pmf)
		self.save(ignore_version=True)

		# Set props used when generating the Dockerfile
		self._set_additional_packages()
		self._set_container_mounts()

		dockerfile = self._generate_dockerfile()
		self._add_build_steps(dockerfile)
		self._add_post_build_steps(no_push)

		self._copy_config_files()
		self._generate_redis_cache_config()
		self._generate_supervisor_config()
		self._generate_apps_txt()
		self.generate_ssh_keys()

	def _clone_repos(self):
		apps_directory = os.path.join(self.build_directory, "apps")
		os.mkdir(apps_directory)

		repo_path_map: dict[str, str] = {}

		for app in self.apps:
			repo_path_map[app.app] = self._clone_app_repo(app)
			app.app_name = self._get_app_name(app.app)
			self.save(ignore_version=True)
			frappe.db.commit()

		return repo_path_map

	def _clone_app_repo(self, app: "DeployCandidateApp") -> str:
		"""
		Clones the app repository if it has not been cloned and
		copies it into the build context directory.

		Returned path points to the repository that needs to be
		validated.
		"""
		if not (step := self.get_step("clone", app.app)):
			raise frappe.ValidationError(f"App {app.app} clone step not found")

		if not self.build_directory:
			raise frappe.ValidationError("Build Directory not set")

		step.command = f"git clone {app.app}"
		source, cloned = frappe.db.get_value(
			"App Release",
			app.release,
			["clone_directory", "cloned"],
		)

		if cloned:
			step.cached = True
			step.status = "Success"
		else:
			source = self._clone_release_update_step(app.release, step)

		target = os.path.join(self.build_directory, "apps", app.app)
		shutil.copytree(source, target, symlinks=True)

		"""
		Pullable updates don't need cloning as they get cloned when
		the app is checked for possible pullable updates in:

		self.get_pull_update_dict
			└─ app_release.get_changed_files_between_hashes
		"""
		if app.pullable_release:
			source = frappe.get_value("App Release", app.pullable_release, "clone_directory")
			target = os.path.join(self.build_directory, "app_updates", app.app)
			shutil.copytree(source, target, symlinks=True)

		return target

	def _clone_release_update_step(self, release: str, step: "DeployCandidateBuildStep"):
		step.status = "Running"
		start_time = now()

		self.save(ignore_version=True)
		frappe.db.commit()

		release: "AppRelease" = frappe.get_doc(
			"App Release",
			release,
			for_update=True,
		)
		release._clone()

		end_time = now()
		step.duration = frappe.utils.rounded((end_time - start_time).total_seconds(), 1)
		step.output = release.output
		step.status = "Success"
		return release.clone_directory

	def _update_packages(self, pmf: PackageManagerFiles):
		existing_apt_packages = set()
		for pkgs in self.packages:
			if pkgs.package_manager != "apt":
				continue
			for p in pkgs.package.split(" "):
				existing_apt_packages.add(p)

		"""
		Individual apps can mention apt dependencies in their pyproject.toml.

		For Example:
		```
		[deploy.dependencies.apt]
		packages = [
			"ffmpeg",
			"libsm6",
			"libxext6",
		]
		```

		For each app, these are grouped together into a single package row.
		"""
		for app in self.apps:
			pyproject = pmf[app.app]["pyproject"] or {}
			deps = pyproject.get("deploy", {}).get("dependencies", {})
			pkgs = deps.get("apt", {}).get("packages", [])

			app_packages = []
			for p in pkgs:
				if p in existing_apt_packages:
					continue
				existing_apt_packages.add(p)
				app_packages.append(p)

			if not app_packages:
				continue

			package = dict(package_manager="apt", package=" ".join(app_packages))
			self.append("packages", package)

	def _set_additional_packages(self):
		"""
		additional_packages is used when rendering the Dockerfile template
		"""
		self.additional_packages = []
		dep_versions = {d.dependency: d.version for d in self.dependencies}
		for p in self.packages:

			#  second clause cause: '/opt/certbot/bin/pip'
			if p.package_manager not in ["apt", "pip"] and not p.package_manager.endswith(
				"/pip"
			):
				continue

			prerequisites = frappe.render_template(p.package_prerequisites, dep_versions)
			package = dict(
				package_manager=p.package_manager,
				package=p.package,
				prerequisites=prerequisites,
				after_install=p.after_install,
			)
			self.additional_packages.append(package)

	def _set_container_mounts(self):
		self.container_mounts = frappe.get_all(
			"Release Group Mount",
			{"parent": self.group, "is_absolute_path": False},
			["destination"],
			order_by="idx",
		)

	def _generate_dockerfile(self):
		dockerfile = os.path.join(self.build_directory, "Dockerfile")
		with open(dockerfile, "w") as f:
			dockerfile_template = "press/docker/Dockerfile"

			for d in self.dependencies:
				if d.dependency == "BENCH_VERSION" and d.version == "5.2.1":
					dockerfile_template = "press/docker/Dockerfile_Bench_5_2_1"

			content = frappe.render_template(dockerfile_template, {"doc": self}, is_path=True)
			f.write(content)
			return content

	def _add_build_steps(self, dockerfile: str):
		"""
		This function adds build steps that take place inside docker build.
		These steps are added from the generated Dockerfile.

		Build steps are updated when docker build runs and prints a string of
		the following format `#stage-{ stage_slug }-{ step_slug }` to the output.

		To add additional build steps:
		- Update STAGE_SLUG_MAP
		- Update STEP_SLUG_MAP
		- Update get_build_stage_and_step
		"""
		app_titles = {a.app: a.title for a in self.apps}

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

	def _add_post_build_steps(self, no_push: bool):
		slugs = []
		if not no_push:
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

	def _copy_config_files(self):
		for target in ["common_site_config.json", "supervisord.conf", ".vimrc"]:
			shutil.copy(
				os.path.join(frappe.get_app_path("press", "docker"), target), self.build_directory
			)

		for target in ["config", "redis"]:
			shutil.copytree(
				os.path.join(frappe.get_app_path("press", "docker"), target),
				os.path.join(self.build_directory, target),
				symlinks=True,
			)

	def _generate_redis_cache_config(self):
		redis_cache_conf = os.path.join(self.build_directory, "config", "redis-cache.conf")
		with open(redis_cache_conf, "w") as f:
			redis_cache_conf_template = "press/docker/config/redis-cache.conf"
			content = frappe.render_template(
				redis_cache_conf_template, {"doc": self}, is_path=True
			)
			f.write(content)

	def _generate_supervisor_config(self):
		supervisor_conf = os.path.join(self.build_directory, "config", "supervisor.conf")
		with open(supervisor_conf, "w") as f:
			supervisor_conf_template = "press/docker/config/supervisor.conf"
			content = frappe.render_template(
				supervisor_conf_template, {"doc": self}, is_path=True
			)
			f.write(content)

	def _generate_apps_txt(self):
		apps_txt = os.path.join(self.build_directory, "apps.txt")
		with open(apps_txt, "w") as f:
			content = "\n".join([app.app_name for app in self.apps])
			f.write(content)

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
				app_name = re.search(r'name\s*=\s*[\'"](.*)[\'"]', f.read().decode("utf-8"))[1]

		if app_name and app != app_name:
			return app_name

		return app

	def _get_app_pyproject(self, app):
		apps_path = os.path.join(self.build_directory, "apps")
		pyproject_path = os.path.join(apps_path, app, "pyproject.toml")
		if not os.path.exists(pyproject_path):
			return {}

		return load_pyproject(app, pyproject_path)

	def _run_docker_build(self, no_cache: bool = False):
		command = self._get_build_command(no_cache)
		environment = self._get_build_environment()
		output = self.run(
			command,
			environment,
		)
		self._parse_build_output(output)

	def _parse_build_output(self, output: "Generator[str, Any, None]"):
		if not self.build_output_parser:
			self.build_output_parser = DockerBuildOutputParser(self)
		self.build_output_parser.parse_and_update(output)

	def _get_build_environment(self):
		environment = os.environ.copy()
		environment.update(
			{"DOCKER_BUILDKIT": "1", "BUILDKIT_PROGRESS": "plain", "PROGRESS_NO_TRUNC": "1"}
		)

		docker_remote_builder_ssh = frappe.db.get_value(
			"Press Settings",
			None,
			"docker_remote_builder_ssh",
		)
		if docker_remote_builder_ssh:
			# Connect to Remote Docker Host if configured
			environment.update({"DOCKER_HOST": f"ssh://root@{docker_remote_builder_ssh}"})

		return environment

	def _get_build_command(self, no_cache: bool):
		command = self.base_build_command
		if no_cache:
			command += " --no-cache"

		command += f" --tag {self.docker_image}"
		command += " ."
		return command

	def run(self, command, environment=None, directory=None):
		process = Popen(
			shlex.split(command),
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			env=environment,
			cwd=directory or self.build_directory,
			universal_newlines=True,
		)
		for line in process.stdout:
			yield line
		process.stdout.close()
		return_code = process.wait()
		if return_code:
			raise subprocess.CalledProcessError(return_code, command)

	def _push_docker_image(self):
		settings = frappe.db.get_value(
			"Press Settings",
			None,
			[
				"docker_registry_url",
				"docker_registry_username",
				"docker_registry_password",
				"docker_remote_builder_ssh",
			],
			as_dict=True,
		)
		environment = os.environ.copy()
		if settings.docker_remote_builder_ssh:
			# Connect to Remote Docker Host if configured
			environment.update(
				{"DOCKER_HOST": f"ssh://root@{settings.docker_remote_builder_ssh}"}
			)

		client = docker.from_env(environment=environment)
		if not self.upload_step_updater:
			self.upload_step_updater = UploadStepUpdater(self)
		self.upload_step_updater.start()
		try:
			client.login(
				registry=settings.docker_registry_url,
				username=settings.docker_registry_username,
				password=settings.docker_registry_password,
			)
			output = client.images.push(
				self.docker_image_repository,
				self.docker_image_tag,
				stream=True,
				decode=True,
			)
			self.upload_step_updater.process(output)
		except Exception:
			self.upload_step_updater.end("Failure")
			log_error("Push Docker Image Failed", doc=self)
			raise

	def generate_ssh_keys(self):
		ca = frappe.get_value("Press Settings", None, "ssh_certificate_authority")
		if ca is None:
			return

		ca = frappe.get_doc("SSH Certificate Authority", ca)
		ssh_directory = os.path.join(self.build_directory, "config", "ssh")

		self.generate_host_keys(ca, ssh_directory)
		self.generate_user_keys(ca, ssh_directory)

		ca_public_key = os.path.join(ssh_directory, "ca.pub")
		with open(ca_public_key, "w") as f:
			f.write(ca.public_key)

		# Generate authorized principal file
		principals = os.path.join(ssh_directory, "principals")
		with open(principals, "w") as f:
			f.write(f"restrict,pty {self.group}")

	def generate_host_keys(self, ca, ssh_directory):
		# Generate host keys
		list(
			self.run(
				f"ssh-keygen -C {self.name} -t rsa -b 4096 -N '' -f ssh_host_rsa_key",
				directory=ssh_directory,
			)
		)

		# Generate host Certificate
		host_public_key_path = os.path.join(ssh_directory, "ssh_host_rsa_key.pub")
		ca.sign(self.name, None, "+52w", host_public_key_path, 0, host_key=True)

	def generate_user_keys(self, ca, ssh_directory):
		# Generate user keys
		list(
			self.run(
				f"ssh-keygen -C {self.name} -t rsa -b 4096 -N '' -f id_rsa",
				directory=ssh_directory,
			)
		)

		# Generate user certificates
		user_public_key_path = os.path.join(ssh_directory, "id_rsa.pub")
		ca.sign(self.name, [self.group], "+52w", user_public_key_path, 0)

		user_private_key_path = os.path.join(ssh_directory, "id_rsa")
		with open(user_private_key_path) as f:
			self.user_private_key = f.read()

		with open(user_public_key_path) as f:
			self.user_public_key = f.read()

		user_certificate_path = os.path.join(ssh_directory, "id_rsa-cert.pub")
		with open(user_certificate_path) as f:
			self.user_certificate = f.read()

		# Remove user key files
		os.remove(user_private_key_path)
		os.remove(user_public_key_path)
		os.remove(user_certificate_path)

	def get_certificate(self):
		return {
			"id_rsa": self.user_private_key,
			"id_rsa.pub": self.user_public_key,
			"id_rsa-cert.pub": self.user_certificate,
		}

	def update_step(self, stage_slug: str, step_slug: str, update_dict: dict[str, Any]):
		step = self.get_step(stage_slug, step_slug)
		if not step:
			return

		for key, value in update_dict.items():
			step.set(key, value)

	def get_step(
		self, stage_slug: str, step_slug: str
	) -> "Optional[DeployCandidateBuildStep]":
		return find(
			self.build_steps,
			lambda x: x.stage_slug == stage_slug and x.step_slug == step_slug,
		)

	def create_deploy(self):
		deploy_doc = None
		servers = frappe.get_doc("Release Group", self.group).servers
		servers = [server.server for server in servers]
		deploy_doc = frappe.db.exists(
			"Deploy", {"group": self.group, "candidate": self.name, "staging": False}
		)

		if deploy_doc or not servers:
			return

		return self._create_deploy(servers)

	def _create_deploy(self, servers: List[str]):
		deploy = frappe.get_doc(
			{
				"doctype": "Deploy",
				"group": self.group,
				"candidate": self.name,
				"benches": [{"server": server} for server in servers],
			}
		).insert()
		return deploy

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

	def get_dependency_version(self, dependency: str, as_env: bool = False):
		if dependency.islower():
			dependency = dependency.upper() + "_VERSION"

		version = find(self.dependencies, lambda x: x.dependency == dependency).version

		if as_env:
			return f"{dependency} {version}"

		return version

	def get_pull_update_dict(self) -> dict[str, AppReleasePair]:
		"""
		Returns a dict of apps with:

		`old` hash: for which there already exist cached layers from previously
		deployed Benches that have been created from this Deploy Candidate.

		`new` hash: which can just be 'git pull' updated, i.e. a new layer does
		not need to be built for them from scratch.
		"""

		# Deployed Benches from current DC with (potentially) cached layers
		benches = frappe.get_all(
			"Bench", filters={"group": self.group, "status": "Active"}, limit=1
		)
		if not benches:
			return {}

		bench_name = benches[0]["name"]
		deployed_apps = frappe.get_all(
			"Bench App",
			filters={"parent": bench_name},
			fields=["app", "source", "hash"],
		)
		deployed_apps_map = {app.app: app for app in deployed_apps}

		pull_update: dict[str, AppReleasePair] = {}

		for app in self.apps:
			app_name = app.app

			"""
			If True, new app added to the Release Group. Downstream layers will
			be rebuilt regardless of layer change.
			"""
			if app_name not in deployed_apps_map:
				break

			deployed_app = deployed_apps_map[app_name]

			"""
			If True, app source updated in Release Group. Downstream layers may
			have to be rebuilt. Erring on the side of caution.
			"""
			if deployed_app["source"] != app.source:
				break

			update_hash = app.hash
			deployed_hash = deployed_app["hash"]

			if update_hash == deployed_hash:
				continue

			changes = get_changed_files_between_hashes(
				app.source,
				deployed_hash,
				update_hash,
			)
			# deployed commit is after update commit
			if not changes:
				break

			file_diff, pair = changes
			if not can_pull_update(file_diff):
				"""
				If current app is not being pull_updated, then no need to
				pull update apps later in the sequence.

				This is because once an image layer hash changes all layers
				after it have to be rebuilt.
				"""
				break

			pull_update[app_name] = pair
		return pull_update

	def _get_docker_remote_builder_server(self):
		server = frappe.get_value("Release Group", self.group, "docker_remote_builder_server")
		if not server:
			server = frappe.get_value("Press Settings", None, "docker_remote_builder_server")
		return server

	def get_first_step(
		self, key: str, value: str | list[str]
	) -> "Optional[DeployCandidateBuildStep]":
		if isinstance(value, str):
			value = [value]

		for build_step in self.build_steps:
			if build_step.get(key) not in value:
				continue
			return build_step
		return None

	def get_duplicate_dc(self) -> "Optional[DeployCandidate]":
		rg: "ReleaseGroup" = frappe.get_doc("Release Group", self.group)
		if not (dc := rg.create_deploy_candidate()):
			return

		# Set new DC apps to pull from the same sources
		new_app_map = {a.app: a for a in dc.apps}
		for app in self.apps:
			if not (new_app := new_app_map.get(app.app)):
				continue

			new_app.hash = app.hash
			new_app.release = app.release
			new_app.source = app.source

		# Remove apps from new DC if they aren't in the old DC
		old_app_map = {a.app: a for a in self.apps}
		for app in dc.apps:
			if old_app_map.get(app.app):
				continue

			dc.remove(app)

		self.save()
		return dc


def can_pull_update(file_paths: list[str]) -> bool:
	"""
	Updated app files between current and previous build
	that do not cause get-app to update the filesystem can
	be git pulled.

	Function returns True ONLY if all files are of this kind.
	"""
	return all(pull_update_file_filter(fp) for fp in file_paths)


def pull_update_file_filter(file_path: str) -> bool:
	blacklist = [
		# Requires pip install
		"requirements.txt",
		"pyproject.toml",
		"setup.py",
		# Requires yarn install, build
		"package.json",
		".vue",
		".ts",
		".jsx",
		".tsx",
		".scss",
	]
	if any(file_path.endswith(f) for f in blacklist):
		return False

	# Non build requiring frontend files
	for ext in [".html", ".js", ".css"]:
		if not file_path.endswith(ext):
			continue

		if "/public/" in file_path or "/www/" in file_path:
			return True

		# Probably requires build
		else:
			return False

	return True


def cleanup_build_directories():
	# Cleanup Build Directories for Deploy Candidates older than a day
	candidates = frappe.get_all(
		"Deploy Candidate",
		{
			"status": ("!=", "Draft"),
			"build_directory": ("is", "set"),
			"creation": ("<=", frappe.utils.add_to_date(None, hours=-6)),
		},
		order_by="creation asc",
		pluck="name",
		limit=100,
	)
	for candidate in candidates:
		try:
			frappe.get_doc("Deploy Candidate", candidate).cleanup_build_directory()
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback()
			log_error(
				title="Deploy Candidate Build Cleanup Error", exception=e, candidate=candidate
			)

	# Delete all temporary files created by the build process
	glob_path = os.path.join(tempfile.gettempdir(), f"{tempfile.gettempprefix()}*.tar.gz")
	six_hours_ago = frappe.utils.add_to_date(None, hours=-6)
	for file in glob.glob(glob_path):
		# Use local time to compare timestamps
		if os.stat(file).st_ctime < six_hours_ago.timestamp():
			os.remove(file)


def ansi_escape(text):
	# Reference:
	# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
	ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
	return ansi_escape.sub("", text)


@frappe.whitelist()
def desk_app(doctype, txt, searchfield, start, page_len, filters):
	return frappe.get_all(
		"Release Group App",
		filters={"parent": filters["release_group"]},
		fields=["app"],
		as_list=True,
	)


def delete_draft_candidates():
	candidates = frappe.get_all(
		"Deploy Candidate",
		{
			"status": "Draft",
			"creation": ("<=", frappe.utils.add_days(None, -1)),
		},
		order_by="creation asc",
		pluck="name",
		limit=1000,
	)

	for candidate in candidates:
		if frappe.db.exists("Bench", {"candidate": candidate}):
			frappe.db.set_value(
				"Deploy Candidate", candidate, "status", "Success", update_modified=False
			)
			frappe.db.commit()
			continue
		else:
			try:
				frappe.delete_doc("Deploy Candidate", candidate, delete_permanently=True)
				frappe.db.commit()
			except Exception:
				log_error("Draft Deploy Candidate Deletion Error", candidate=candidate)
				frappe.db.rollback()


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Deploy Candidate"
)


@frappe.whitelist()
def toggle_builds(suspend):
	frappe.only_for("System Manager")
	frappe.db.set_single_value("Press Settings", "suspend_builds", suspend)


def run_scheduled_builds():
	candidates = frappe.get_all(
		"Deploy Candidate",
		{"status": "Scheduled", "scheduled_time": ("<=", frappe.utils.now_datetime())},
		limit=1,
	)
	for candidate in candidates:
		try:
			candidate: "DeployCandidate" = frappe.get_doc("Deploy Candidate", candidate)
			candidate.schedule_build_and_deploy(is_running_scheduled=True)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Scheduled Deploy Candidate Error", candidate=candidate)


# Key: stage_slug
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
	("validate", "dependencies"): "Validate Dependencies",
	("mounts", "create"): "Prepare Mounts",
	("upload", "image"): "Docker Image",
	("package", "context"): "Build Context",
	("upload", "context"): "Build Context",
}


def get_build_stage_and_step(
	stage_slug: str, step_slug: str, app_titles: dict[str, str] = None
) -> Tuple[str, str]:
	stage = STAGE_SLUG_MAP.get(stage_slug, stage_slug)
	step = step_slug
	if stage_slug == "clone" or stage_slug == "apps":
		step = app_titles.get(step_slug, step_slug)
	else:
		step = STEP_SLUG_MAP.get((stage_slug, step_slug), step_slug)
	return (stage, step)


def is_suspended() -> bool:
	return bool(frappe.db.get_single_value("Press Settings", "suspend_builds"))


def get_remote_step_output(
	step_name: Literal["build", "push"],
	output_data: dict,
	response_data: Optional[dict],
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
		if (
			not isinstance(commands, list)
			or len(commands) == 0
			or not isinstance(commands[0], dict)
		):
			continue

		output = commands[0].get("output")
		if not isinstance(output, str):
			continue

		try:
			return json.loads(output).get(step_name, [])
		except AttributeError:
			continue
		except json.JSONDecodeError:
			continue

	return None
