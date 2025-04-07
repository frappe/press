# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import os
import shutil
import typing
from functools import cached_property

import frappe
from frappe.model.document import Document

from press.press.doctype.deploy_candidate.utils import get_package_manager_files
from press.utils import get_current_team

if typing.TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_app.deploy_candidate_app import DeployCandidateApp


class RemoteBuild(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.build_steps.build_steps import BuildSteps

		build_steps: DF.Table[BuildSteps]
		deploy_candidate: DF.Link
		name: DF.Int | None
		no_build: DF.Check
		no_cache: DF.Check
		no_push: DF.Check
		status: DF.Literal["Pending", "Preparing", "Running", "Success", "Failure"]
	# end: auto-generated types

	def set_build_step(
		self,
		step_name: str,
		step_status: str,
		step_cached: bool = False,
		step_output: str | None = None,
		step_command: str | None = None,
	):
		"""Update the step or add the step to the build steps list"""
		step_data = {
			"step": step_name,
			"step_output": step_output,
			"step_cached": step_cached,
			"step_status": step_status,
			"step_command": step_command,
		}

		for idx, step in enumerate(self.build_steps):
			if step.get("step") == step_name:
				step_data["step_output"] = step_output if step_output is not None else step.get("step_output")
				step_data["step_cached"] = (
					step_cached if step_cached is not None else step.get("step_cached", False)
				)
				step_data["step_status"] = (
					step_status if step_status is not None else step.get("step_status", "Pending")
				)
				step_data["step_command"] = (
					step_command if step_command is not None else step.get("step_command")
				)
				self.build_steps[idx] = step_data
				return

		self.append("build_steps", step_data)

	@cached_property
	def candidate(self) -> DeployCandidate:
		return frappe.get_doc("Deploy Candidate", self.deploy_candidate)

	def _clone_app(self, app: DeployCandidateApp):
		step_name = f"Clone Repository {app.app}"
		command = f"git clone {app.app}"
		source, cloned = frappe.get_value("App Release", app.release, ["clone_directory", "cloned"])

		if cloned and os.path.exists(source):
			self.set_build_step(
				step_name=step_name,
				step_status="Success",
				step_cached=True,
				step_command=command,
				step_output="",
			)
		else:
			self.set_build_step(step_name, "Running", command=command)
			release: AppRelease = frappe.get_doc("App Release", app.release, for_update=True)
			source = release._clone(force=True)
			self.set_build_step(step_name, "Success", command=command)

		target = os.path.join(self.candidate.build_directory, "apps", app.app)
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

		return repo_path_map

	def _prepare_build_context(self):
		repo_path_map = self._clone_repositories()
		pmf = get_package_manager_files(repo_path_map)
		self.candidate._run_prebuild_validations_and_update_step(pmf)

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
		self.candidate._generate_dockerfile()
		# For now we don't add steps here.
		# self.candidate._add_build_steps(dockerfile)

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

	def _run_agent_jobs(self):
		for file in os.scandir(self.candidate.build_directory):
			print(file.name)

	def _start_build(self):
		self.candidate._update_docker_image_metadata()  # we just assing a docker image tag

		if self.no_build:
			return

		self._run_agent_jobs()

	def _build(self):
		self.status = "Preparing"
		# try:
		self._prepare_build()
		self._start_build()
		# except Exception as exc:
		# 	print(exc)

	def reset_build_steps(self):
		self.build_steps.clear()

	def pre_build(self):
		self.reset_build_steps()
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

		self._build()
		# frappe.enqueue(self._build, queue=queue, timeout=2400, enqueue_after_commit=True)

		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	def after_insert(self):
		self.pre_build()

	@frappe.whitelist(allow_guest=True)
	def update_build_step(self, step_name: str, status: str, output: str):
		"""Update build steps received from the agent"""
		...
