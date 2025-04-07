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
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


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

	@cached_property
	def candidate(self) -> DeployCandidate:
		return frappe.get_doc("Deploy Candidate", self.deploy_candidate)

	def _handle_older_bench_deps(self):
		# Now now let older bench versions run as it is.
		dockerfile_template = "press/docker/Dockerfile_Bench_5_2_1"
		with open(os.path.join(self.candidate.build_directory, "Dockerfile"), "w") as f:
			content = frappe.render_template(dockerfile_template, {"doc": self.candidate}, is_path=True)
			f.write(content)
			return content

	def _generate_dockerfile(self):
		for d in self.candidate.dependencies:
			if d.dependency == "BENCH_VERSION" and d.version == "5.2.1":
				return self._handle_older_bench_deps()

		docker_folder = os.path.join(self.candidate.build_directory, "docker")
		if os.path.exists(docker_folder):
			shutil.rmtree(docker_folder)

		os.mkdir(docker_folder)
		context_required_for = ["Dockerfile.frappe", "Dockerfile.wkhtmltopdf"]

		for docker_step in os.scandir("press/docker/docker_steps"):
			if docker_step.name in context_required_for:
				with open(os.path.join(docker_folder, docker_step.name), "w") as docker_step_file:
					content = frappe.render_template(docker_step.path, {"doc": self.candidate}, is_path=True)
					docker_step_file.write(content)
			else:
				shutil.copy(docker_step.path, os.path.join(docker_folder, docker_step.name))

		return None

	def _prepare_build_context(self):
		# TODO: Fix this we need to find a way to bypass build step in this case
		# And add our own step
		repo_path_map = self.candidate._clone_repos()
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
		dockerfile = self._generate_dockerfile()
		if dockerfile:
			# Older bench version
			self.candidate._add_build_steps(dockerfile)

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
		self.candidate._prepare_build_context(self.no_push)

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
		try:
			self._prepare_build()
			self._start_build()
		except Exception as exc:
			print(exc)

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
