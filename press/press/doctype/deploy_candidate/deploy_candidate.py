# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import json
import os
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
from subprocess import Popen
from typing import List

import docker
import dockerfile

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
from press.press.doctype.press_notification.press_notification import (
	create_new_notification,
)
from press.press.doctype.release_group.release_group import ReleaseGroup
from press.press.doctype.server.server import Server
from press.utils import get_current_team, log_error


class DeployCandidate(Document):
	dashboard_fields = [
		"name",
		"status",
		"creation",
		"deployed",
		"build_steps",
		"build_start",
		"build_end",
		"build_duration",
		"apps",
		"group",
	]

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
		self.status = "Pending"
		if not kwargs.get("no_cache"):
			self._update_app_releases()
		self.add_build_steps()
		self.save()
		user, session_data, team, = (
			frappe.session.user,
			frappe.session.data,
			get_current_team(True),
		)
		frappe.set_user(frappe.get_value("Team", team.name, "user"))
		# self._build()
		frappe.enqueue_doc(
			self.doctype, self.name, method, timeout=2400, enqueue_after_commit=True, **kwargs
		)
		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	@frappe.whitelist()
	def build(self):
		self.pre_build(method="_build")

	@frappe.whitelist()
	def build_without_cache(self):
		self.pre_build(method="_build", no_cache=True)

	@frappe.whitelist()
	def deploy_to_staging(self):
		"""Deploy a bench on staging server and also create a staging site."""
		self.build_and_deploy(staging=True)

	@frappe.whitelist()
	def promote_to_production(self):
		if not self.staged:
			frappe.throw("Cannot promote unstaged candidate to production")
		self._deploy()

	@frappe.whitelist()
	def deploy_to_production(self):
		if (
			frappe.db.get_single_value("Press Settings", "suspend_builds")
			and not self._is_docker_remote_builder_server_configured()
		):
			if self.status != "Scheduled":
				# Schedule build to be run ASAP.
				self.status = "Scheduled"
				self.scheduled_time = frappe.utils.now_datetime()
				self.save()
				frappe.db.commit()
			return
		self.build_and_deploy()

	def build_and_deploy(self, staging: bool = False):
		self.pre_build(method="_build_and_deploy", staging=staging)

	def _build_and_deploy(self, staging: bool):
		self._build(deploy_after_build=True, deploy_to_staging=staging)

	def _deploy(self, staging=False):
		try:
			self.create_deploy(staging)
		except Exception:
			log_error("Deploy Creation Error", candidate=self.name)

	def _build(self, no_cache=False, deploy_after_build=False, deploy_to_staging=False):
		def _mark_build_as_running():
			self.status = "Running"
			self.save()
			frappe.db.commit()

		self.status = "Preparing"
		self.build_start = now()
		self.is_single_container = True
		self.is_ssh_enabled = True
		if not no_cache and self.use_app_cache:
			self._set_app_cached_flags()
		self.save()
		frappe.db.commit()

		try:
			self._prepare_build_directory()
			self._prepare_build_context()

			# Fetch Remote Docker Builder Config
			settings = frappe.db.get_value(
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
			if settings.docker_registry_namespace:
				namespace = f"{settings.docker_registry_namespace}/{settings.domain}"
			else:
				namespace = f"{settings.domain}"
			self.docker_image_repository = (
				f"{settings.docker_registry_url}/{namespace}/{self.group}"
			)
			self.docker_image_tag = self.name
			self.docker_image = f"{self.docker_image_repository}:{self.docker_image_tag}"
			remote_build_server = self._get_docker_remote_builder_server()
			if remote_build_server:
				agent = Agent(remote_build_server)
				# Upload build context to remote docker builder
				build_context_archieve_filepath = self._tar_build_context()
				uploaded_filename = None
				with open(build_context_archieve_filepath, "rb") as f:
					uploaded_filename = agent.upload_build_context_for_docker_build(f)
				if not uploaded_filename:
					raise Exception("Failed to upload build context to remote docker builder")
				agent.build_docker_image(
					{
						"deploy_candidate": self.name,
						"deploy_after_build": deploy_after_build,
						"deploy_to_staging": deploy_to_staging,
						"filename": uploaded_filename,
						"image_repository": self.docker_image_repository,
						"image_tag": self.docker_image_tag,
						"no_cache": no_cache,
						"registry": {
							"password": settings.docker_registry_password,
							"url": settings.docker_registry_url,
							"username": settings.docker_registry_username,
						},
						"build_steps": [
							{
								"stage": step.stage,
								"stage_slug": step.stage_slug,
								"step": step.step,
								"step_slug": step.step_slug,
								"status": step.status,
								"duration": step.duration,
								"cached": step.cached,
								"step_index": step.step_index,
								"hash": step.hash,
								"command": step.command,
								"output": step.output,
								"lines": step.lines,
							}
							for step in self.build_steps
						],
					}
				)
				_mark_build_as_running()
			else:
				_mark_build_as_running()
				self._run_docker_build(no_cache)
				self._push_docker_image()
				self._build_successful()
				self._build_end()

				# Deploy if deploy_after_build set
				if self.status == "Success" and deploy_after_build:
					self._deploy(deploy_to_staging)
		except Exception:
			log_error("Deploy Candidate Build Exception", name=self.name)
			self._build_failed()
			self._build_end()
			raise

	def _build_failed(self):
		self.status = "Failure"
		bench_update = frappe.get_all(
			"Bench Update", {"status": "Running", "candidate": self.name}, pluck="name"
		)
		if bench_update:
			frappe.db.set_value("Bench Update", bench_update[0], "status", "Failure")
		self.save()
		frappe.db.commit()

	def _build_successful(self):
		self.status = "Success"
		bench_update = frappe.get_all(
			"Bench Update", {"status": "Running", "candidate": self.name}, pluck="name"
		)
		if bench_update:
			frappe.db.set_value("Bench Update", bench_update[0], "status", "Build Successful")
		self.save()
		frappe.db.commit()

	def _build_end(self):
		self.build_end = now()
		self.build_duration = self.build_end - self.build_start
		self.save()
		frappe.db.commit()

	def add_build_steps(self):
		if self.build_steps:
			return

		self.steps_additional_packages = []
		self._mounts = []

		self._prepare_packages()
		self._prepare_mounts()

		# stage_slug, step_slug, stage, step
		preparation_steps = [
			("pre", "essentials", "Setup Prerequisites", "Install Essential Packages"),
			("pre", "redis", "Setup Prerequisites", "Install Redis"),
			("pre", "python", "Setup Prerequisites", "Install Python"),
			("pre", "wkhtmltopdf", "Setup Prerequisites", "Install wkhtmltopdf"),
			("pre", "fonts", "Setup Prerequisites", "Install Fonts"),
		]

		if self.steps_additional_packages:
			preparation_steps.extend(self.steps_additional_packages)

		if frappe.get_value("Team", self.team, "is_code_server_user"):
			preparation_steps.extend(
				[
					("pre", "code-server", "Setup Prerequisites", "Install Code Server"),
				]
			)

		preparation_steps.extend(
			[
				("pre", "node", "Setup Prerequisites", "Install Node.js"),
				("pre", "yarn", "Setup Prerequisites", "Install Yarn"),
				("pre", "pip", "Setup Prerequisites", "Install pip"),
				("bench", "bench", "Setup Bench", "Install Bench"),
				("bench", "env", "Setup Bench", "Setup Virtual Environment"),
			]
		)

		clone_steps = []
		app_install_steps = []
		pull_update_steps = []
		mount_step = []

		if self._mounts:
			mount_step.extend(
				[
					("mounts", "create", "Setup Mounts", "Prepare Mounts"),
				]
			)

		for app in self.apps:
			clone_steps.append(("clone", app.app, "Clone Repositories", app.title))
			app_install_steps.append(("apps", app.app, "Install Apps", app.title))

			if app.pullable_release:
				pull_update_steps.append(("pull", app.app, "Pull Updates", app.title))

		validation_steps = [
			("validate", "dependencies", "Run Validations", "Validate Dependencies"),
		]

		steps = [
			*clone_steps,
			*preparation_steps,
			*app_install_steps,
			*pull_update_steps,
			*validation_steps,
			*mount_step,
		]

		for stage_slug, step_slug, stage, step in steps:
			self.append(
				"build_steps",
				{
					"status": "Pending",
					"stage_slug": stage_slug,
					"step_slug": step_slug,
					"stage": stage,
					"step": step,
				},
			)
		self.append(
			"build_steps",
			{
				"status": "Pending",
				"stage_slug": "upload",
				"step_slug": "upload",
				"stage": "Upload",
				"step": "Docker Image",
			},
		)
		self.save()

	def _prepare_packages(self):
		packages = []
		_variables = {d.dependency: d.version for d in self.dependencies}

		for p in self.packages:
			_package_manager = p.package_manager.split("/")[-1]

			if _package_manager in ["apt", "pip"]:
				self.steps_additional_packages.append(
					[
						"pre",
						p.package,
						"Setup Prerequisites",
						f"Install package {p.package}",
					]
				)
				packages.append(
					{
						"package_manager": p.package_manager,
						"package": p.package,
						"prerequisites": frappe.render_template(p.package_prerequisites, _variables),
						"after_install": p.after_install,
					}
				)

		self.apt_packages = json.dumps(packages)

	def _prepare_mounts(self):
		self._mounts = frappe.get_all(
			"Release Group Mount",
			{"parent": self.group},
			["source", "destination", "is_absolute_path"],
			order_by="idx",
		)

		self.mounts = json.dumps(self._mounts)

	def _set_app_cached_flags(self) -> None:
		for app in self.apps:
			app.use_cached = True

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
		should_update = frappe.get_value(
			"Release Group", self.group, "is_delta_build_enabled"
		)
		if not should_update:
			return

		try:
			update = self.get_pull_update_dict()
		except Exception as e:
			log_error(title="Failed to get Pull Update Dict", data=e)
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

	def _prepare_build_context(self):
		# Create apps directory
		apps_directory = os.path.join(self.build_directory, "apps")
		os.mkdir(apps_directory)

		for app in self.apps:
			source, cloned = frappe.db.get_value(
				"App Release", app.release, ["clone_directory", "cloned"]
			)
			step = find(
				self.build_steps, lambda x: x.stage_slug == "clone" and x.step_slug == app.app
			)
			step.command = f"git clone {app.app}"

			if cloned:
				step.cached = True
				step.status = "Success"
			else:
				step.status = "Running"
				start_time = now()

				self.save(ignore_version=True)
				frappe.db.commit()

				release = frappe.get_doc("App Release", app.release, for_update=True)
				release._clone()
				source = release.clone_directory

				end_time = now()
				step.duration = frappe.utils.rounded((end_time - start_time).total_seconds(), 1)
				step.output = release.output
				step.status = "Success"

			target = os.path.join(self.build_directory, "apps", app.app)
			shutil.copytree(source, target, symlinks=True)
			app.app_name = self._get_app_name(app.app)

			"""
			Pullable updates don't need cloning as they get cloned when
			the app is checked for possible pullable updates in:

			self.get_pull_update_dict
				└─ app_release.get_changed_files_between_hashes
			"""
			if app.pullable_release:
				update_source = frappe.get_value(
					"App Release", app.pullable_release, "clone_directory"
				)
				update_target = os.path.join(self.build_directory, "app_updates", app.app)
				shutil.copytree(update_source, update_target, symlinks=True)

			self.save(ignore_version=True)
			frappe.db.commit()

		self._load_packages()
		self._load_mounts()
		self._generate_dockerfile()
		self._copy_config_files()
		self._generate_redis_cache_config()
		self._generate_supervisor_config()
		self._generate_apps_txt()
		self.generate_ssh_keys()

	def _load_packages(self):
		try:
			self.additional_packages = json.loads(self.apt_packages)
		except Exception:
			# backward compatibility
			self.additional_packages = [
				{"package": p.package} for p in self.packages if p.package_manager == "apt"
			]

	def _load_mounts(self):
		if self.mounts:
			self.container_mounts = json.loads(self.mounts)

	def _generate_dockerfile(self):
		dockerfile = os.path.join(self.build_directory, "Dockerfile")
		with open(dockerfile, "w") as f:
			dockerfile_template = "press/docker/Dockerfile"

			for d in self.dependencies:
				if d.dependency == "BENCH_VERSION" and d.version == "5.2.1":
					dockerfile_template = "press/docker/Dockerfile_Bench_5_2_1"

			content = frappe.render_template(dockerfile_template, {"doc": self}, is_path=True)
			f.write(content)

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

		pyproject_path = os.path.join(apps_path, app, "pyproject.toml")
		config_py_path = os.path.join(apps_path, app, "setup.cfg")
		setup_py_path = os.path.join(apps_path, app, "setup.py")

		if os.path.exists(pyproject_path):
			try:
				from tomli import load
			except ImportError:
				from tomllib import load

			with open(pyproject_path, "rb") as f:
				app_name = load(f).get("project", {}).get("name")

		if not app_name and os.path.exists(config_py_path):
			from setuptools.config import read_configuration

			config = read_configuration(config_py_path)
			app_name = config.get("metadata", {}).get("name")

		if not app_name:
			# retrieve app name from setup.py as fallback
			with open(setup_py_path, "rb") as f:
				app_name = re.search(r'name\s*=\s*[\'"](.*)[\'"]', f.read().decode("utf-8"))[1]

		if app_name and app != app_name:
			return app_name

		return app

	def _tar_build_context(self) -> str:
		"""Creates a tarball of the build context and returns the path to it."""
		tmp_file_path = tempfile.mkstemp(suffix=".tar.gz")[1]
		with tarfile.open(tmp_file_path, "w:gz") as tar:
			tar.add(self.build_directory, arcname=".")
		return tmp_file_path

	command = "docker build"

	def _run_docker_build(self, no_cache=False):
		import platform

		settings = frappe.db.get_value(
			"Press Settings",
			None,
			[
				"domain",
				"docker_registry_url",
				"docker_registry_namespace",
				"docker_remote_builder_ssh",
			],
			as_dict=True,
		)

		# check if it's running on apple silicon mac
		if (
			platform.machine() == "arm64"
			and platform.system() == "Darwin"
			and platform.processor() == "arm"
		):
			self.command = f"{self.command}x build --platform linux/amd64"

		environment = os.environ.copy()
		environment.update(
			{"DOCKER_BUILDKIT": "1", "BUILDKIT_PROGRESS": "plain", "PROGRESS_NO_TRUNC": "1"}
		)

		if settings.docker_remote_builder_ssh:
			# Connect to Remote Docker Host if configured
			environment.update(
				{"DOCKER_HOST": f"ssh://root@{settings.docker_remote_builder_ssh}"}
			)

		if settings.docker_registry_namespace:
			namespace = f"{settings.docker_registry_namespace}/{settings.domain}"
		else:
			namespace = f"{settings.domain}"

		self.docker_image_repository = (
			f"{settings.docker_registry_url}/{namespace}/{self.group}"
		)

		self.docker_image_tag = self.name
		self.docker_image = f"{self.docker_image_repository}:{self.docker_image_tag}"

		if no_cache:
			self.command += " --no-cache"

		self.command += f" -t {self.docker_image}"
		self.command += " ."

		result = self.run(
			self.command,
			environment,
		)
		self._parse_docker_build_result(result)

	def _parse_docker_build_result(self, result):
		lines = []
		last_update = now()
		steps = frappe._dict()
		for line in result:
			line = ansi_escape(line)
			lines.append(line)

			# Strip appended newline
			line = line.strip()

			# Skip blank lines
			if not line:
				continue

			unusual_line = False
			try:
				# Remove step index from line
				step_index, line = line.split(maxsplit=1)
				try:
					step_index = int(step_index[1:])
				except ValueError:
					line = step_index + " " + line
					step_index = sorted(steps)[-1]
					unusual_line = True

				# Parse first line and add step to steps dict
				if step_index not in steps and line.startswith("[stage-"):
					name = line.split("]", maxsplit=1)[1].strip()
					match = re.search("`#stage-(.*)`", name)
					if name.startswith("RUN") and match:
						flags = dockerfile.parse_string(name)[0].flags
						if flags:
							name = name.replace(flags[0], "")
						name = name.replace(match.group(0), "").strip().replace("   ", " \\\n  ")[4:]
						stage_slug, step_slug = match.group(1).split("-", maxsplit=1)
						step = find(
							self.build_steps,
							lambda x: x.stage_slug == stage_slug and x.step_slug == step_slug,
						)

						step.step_index = step_index
						step.command = name
						step.status = "Running"
						step.output = ""

						if stage_slug == "apps":
							step.command = f"bench get-app {step_slug}"
						steps[step_index] = step

				elif step_index in steps:
					# Parse rest of the lines
					step = find(self.build_steps, lambda x: x.step_index == step_index)
					# step = steps[step_index]
					if line.startswith("sha256:"):
						step.hash = line[7:]
					elif line.startswith("DONE"):
						step.status = "Success"
						step.duration = float(line.split()[1][:-1])
					elif line == "CACHED":
						step.status = "Success"
						step.cached = True
					elif line.startswith("ERROR"):
						step.status = "Failure"
						step.output += line[7:] + "\n"

					else:
						if unusual_line:
							# This line doesn't contain any docker step info
							output = line
						else:
							# Preserve additional whitespaces while splitting
							time, _, output = line.partition(" ")
						step.output += output + "\n"
				elif line.startswith("writing image"):
					self.docker_image_id = line.split()[2].split(":")[1]

				# Publish Progress
				if (now() - last_update).total_seconds() > 1:
					self.build_output = "".join(lines)
					self.save(ignore_version=True)
					frappe.db.commit()

					last_update = now()
			except Exception:
				import traceback

				print("Error in parsing line:", line)
				traceback.print_exc()

		self.build_output = "".join(lines)
		self.save()
		frappe.db.commit()

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
		step = find(self.build_steps, lambda x: x.stage_slug == "upload")
		step.status = "Running"
		start_time = now()
		# publish progress
		self.save()
		frappe.db.commit()

		try:
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
			client.login(
				registry=settings.docker_registry_url,
				username=settings.docker_registry_username,
				password=settings.docker_registry_password,
			)

			step.output = ""
			output = []
			last_update = now()

			for line in client.images.push(
				self.docker_image_repository, self.docker_image_tag, stream=True, decode=True
			):
				if "id" not in line.keys():
					continue

				line_output = f'{line["id"]}: {line["status"]} {line.get("progress", "")}'

				existing = find(output, lambda x: x["id"] == line["id"])
				if existing:
					existing["output"] = line_output
				else:
					output.append({"id": line["id"], "output": line_output})

				if (now() - last_update).total_seconds() > 1:
					step.output = "\n".join(ll["output"] for ll in output)
					self.save(ignore_version=True)
					frappe.db.commit()
					last_update = now()

			end_time = now()
			step.output = "\n".join(ll["output"] for ll in output)
			step.duration = frappe.utils.rounded((end_time - start_time).total_seconds(), 1)
			step.status = "Success"

			self.save()
			frappe.db.commit()
		except Exception:
			step.status = "Failure"
			self.save()
			frappe.db.commit()
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

	def create_deploy(self, staging: bool = False):
		deploy_doc = None
		if staging:
			servers = [Server.get_one_staging()]
			if not servers:
				frappe.log_error(title="Staging Server for new benches not found")
		else:
			servers = frappe.get_doc("Release Group", self.group).servers
			servers = [server.server for server in servers]
			deploy_doc = frappe.db.exists(
				"Deploy", {"group": self.group, "candidate": self.name, "staging": False}
			)

		if deploy_doc or not servers:
			return

		return self._create_deploy(servers, staging)

	def _create_deploy(self, servers: List[str], staging=False):
		deploy = frappe.get_doc(
			{
				"doctype": "Deploy",
				"group": self.group,
				"candidate": self.name,
				"benches": [{"server": server} for server in servers],
				"staging": staging,
			}
		).insert()
		if staging:
			self.db_set("staged", True)
		return deploy

	def on_update(self):
		# failure notification
		if self.status == "Failure":
			error_msg = " - ".join(
				frappe.get_value(
					"Deploy Candidate Build Step",
					{"parent": self.name, "status": "Failure"},
					["stage", "step"],
				)
				or []
			)
			group_title = frappe.get_value("Release Group", self.group, "title")

			create_new_notification(
				self.team,
				"Bench Deploy",
				self.doctype,
				self.name,
				f"The scheduled deploy on the bench <b>{group_title}</b> failed at step <b>{error_msg}</b>",
			)
		if self.status == "Running":
			frappe.publish_realtime(
				f"bench_deploy:{self.name}:steps", {"steps": self.build_steps, "name": self.name}
			)
		else:
			frappe.publish_realtime(f"bench_deploy:{self.name}:finished")

	def get_apt_packages(self):
		return " ".join(
			p.package for p in self.packages if p.package_manager in ["apt", "pip"]
		)

	def get_dependency_version(self, dependency):
		version = find(self.dependencies, lambda x: x.dependency == dependency).version
		return f"{dependency} {version}"

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

	def process_docker_image_build_job_update(self, job):
		job = job.get_doc(job.as_dict())
		request_data = json.loads(job.request_data)
		data = find(job["steps"], lambda x: x["step_name"] == "Docker Image Build")["output"]
		if data:
			data = json.loads(data)
		else:
			data = {}
		# Update build output
		self.build_output = data.get("build_output", "")
		# Update build steps
		for step_update in data.get("build_steps", []):
			step = find(
				self.build_steps,
				lambda x: x.stage_slug == step_update["stage_slug"]
				and x.step_slug == step_update["step_slug"],
			)
			step.status = step_update["status"]
			step.cached = step_update["cached"]
			step.command = step_update["command"]
			step.duration = step_update["duration"]
			step.hash = step_update["hash"]
			step.lines = step_update["lines"]
			step.output = step_update["output"]
			step.step_index = step_update["step_index"]

		if job.status == "Running":
			self.status = "Running"
			self.save()
			frappe.db.commit()
		elif job.status == "Failure":
			self._build_failed()
			self._build_end()
		elif job.status == "Success":
			self.docker_image_id = data.get("docker_image_id", "")
			self._build_successful()
			self._build_end()

			# Check if deployment required
			if request_data.get("deploy_after_build"):
				self.create_deploy(request_data.get("deploy_to_staging"))

	def _is_docker_remote_builder_server_configured(self):
		return bool(self._get_docker_remote_builder_server())

	def _get_docker_remote_builder_server(self):
		server = frappe.get_value("Release Group", self.group, "docker_remote_builder_server")
		if not server:
			server = frappe.get_value("Press Settings", None, "docker_remote_builder_server")
		return server

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
			candidate = frappe.get_doc("Deploy Candidate", candidate)
			candidate.deploy_to_production()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error(title="Scheduled Deploy Candidate Error", candidate=candidate)


def process_docker_image_build_job_update(job):
	request_data = json.loads(job.request_data)
	deploy_candidate = frappe.get_doc("Deploy Candidate", request_data["deploy_candidate"])
	deploy_candidate.process_docker_image_build_job_update(job)
