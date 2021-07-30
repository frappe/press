# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import os
import re
import shlex
import shutil
import subprocess
from subprocess import Popen
from typing import List

import docker
import dockerfile
import frappe
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime as now

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.server.server import Server
from press.utils import get_current_team, log_error

# import json


class DeployCandidate(Document):
	def autoname(self):
		group = self.group[6:]
		series = f"deploy-{group}-.######"
		self.name = make_autoname(series)

	def after_insert(self):
		return

	@frappe.whitelist()
	def build(self):
		self.status = "Pending"
		self.add_build_steps()
		self.save()
		user, session_data, team, = (
			frappe.session.user,
			frappe.session.data,
			get_current_team(),
		)
		frappe.set_user(team)
		frappe.enqueue_doc(
			self.doctype, self.name, "_build", timeout=1200, enqueue_after_commit=True
		)
		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

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
		self.build_and_deploy()

	def build_and_deploy(self, staging: bool = False):
		self.status = "Pending"
		self.add_build_steps()
		self.save()
		user, session_data, team, = (
			frappe.session.user,
			frappe.session.data,
			get_current_team(),
		)
		frappe.set_user(team)
		frappe.enqueue_doc(
			self.doctype,
			self.name,
			"_build_and_deploy",
			timeout=1200,
			enqueue_after_commit=True,
			staging=staging,
		)
		frappe.set_user(user)
		frappe.session.data = session_data
		frappe.db.commit()

	def _build_and_deploy(self, staging: bool):
		self._build()
		self._deploy(staging)

	@frappe.whitelist()
	def _deploy(self, staging=False):
		try:
			self.create_deploy(staging)
		except Exception:
			log_error("Deploy Creation Error", candidate=self.name)

	def _build(self):
		self.status = "Running"
		self.build_start = now()
		self.is_single_container = True
		self.save()
		frappe.db.commit()

		try:
			self._prepare_build_directory()
			self._prepare_build_context()
			self._run_docker_build()
			self._push_docker_image()
		except Exception:
			log_error("Deploy Candidate Build Exception", name=self.name)
			self.status = "Failure"
		else:
			self.status = "Success"

		self.build_end = now()
		self.build_duration = self.build_end - self.build_start
		self.save()

	def add_build_steps(self):
		if self.build_steps:
			return

		preparation_steps = [
			("pre", "essentials", "Setup Prerequisites", "Install Essential Packages"),
			("pre", "python", "Setup Prerequisites", "Install Python"),
			("pre", "wkhtmltopdf", "Setup Prerequisites", "Install wkhtmltopdf"),
			("pre", "fonts", "Setup Prerequisites", "Install Fonts"),
			("pre", "node", "Setup Prerequisites", "Install Node.js"),
			("pre", "yarn", "Setup Prerequisites", "Install Yarn"),
			("bench", "bench", "Setup Bench", "Install Bench"),
			("bench", "env", "Setup Bench", "Setup Virtual Environment"),
		]

		clone_steps, app_install_steps = [], []
		for app in self.apps:
			clone_steps.append(("clone", app.app, "Clone Repositories", app.title))
			app_install_steps.append(("apps", app.app, "Install Apps", app.title))

		steps = clone_steps + preparation_steps + app_install_steps

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
		# Create apps directory
		apps_directory = os.path.join(self.build_directory, "apps")
		os.mkdir(apps_directory)

		for app in self.apps:
			source, cloned = frappe.db.get_value(
				"App Release", app.release, ["clone_directory", "cloned"]
			)
			step = find(
				self.build_steps, lambda x: x.stage_slug == "clone" and x.step_slug == app.app,
			)
			step.command = f"git clone {app.app}"

			if cloned:
				step.cached = True
				step.status = "Success"
			else:
				step.status = "Running"
				start_time = now()

				self.save()
				frappe.db.commit()

				release = frappe.get_doc("App Release", app.release)
				release._clone()
				source = release.clone_directory

				end_time = now()
				step.duration = frappe.utils.rounded((end_time - start_time).total_seconds(), 1)
				step.output = release.output
				step.status = "Success"

			target = os.path.join(self.build_directory, "apps", app.app)
			shutil.copytree(source, target)

			self.save()
			frappe.db.commit()

		dockerfile = os.path.join(self.build_directory, "Dockerfile")
		with open(dockerfile, "w") as f:
			dockerfile_template = "press/docker/Dockerfile"
			content = frappe.render_template(dockerfile_template, {"doc": self}, is_path=True)
			f.write(content)

		for target in ["common_site_config.json", "supervisord.conf"]:
			shutil.copy(
				os.path.join(frappe.get_app_path("press", "docker"), target), self.build_directory,
			)

		for target in ["config"]:
			shutil.copytree(
				os.path.join(frappe.get_app_path("press", "docker"), target),
				os.path.join(self.build_directory, target),
			)

	def _run_docker_build(self):
		environment = os.environ
		environment.update(
			{"DOCKER_BUILDKIT": "1", "BUILDKIT_PROGRESS": "plain", "PROGRESS_NO_TRUNC": "1"}
		)

		settings = frappe.db.get_value(
			"Press Settings",
			None,
			["domain", "docker_registry_url", "docker_registry_namespace"],
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

		result = self.run(f"docker build -t {self.docker_image} .", environment)
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

			try:
				# Remove step index from line
				step_index, line = line.split(maxsplit=1)
				step_index = int(step_index[1:])

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
						# Preserve additional whitespaces while splitting
						time, _, output = line.partition(" ")
						step.output += output + "\n"
				elif line.startswith("writing image"):
					self.docker_image_id = line.split()[2].split(":")[1]

				# Publish Progress
				if (now() - last_update).total_seconds() > 1:
					self.build_output = "".join(lines)
					self.save()
					frappe.db.commit()

					last_update = now()
			except Exception:
				import traceback

				traceback.print_exc()

		self.build_output = "".join(lines)
		self.save()
		frappe.db.commit()

	def run(self, command, environment=None):
		process = Popen(
			shlex.split(command),
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			env=environment,
			cwd=self.build_directory,
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
				["docker_registry_url", "docker_registry_username", "docker_registry_password"],
				as_dict=True,
			)

			client = docker.from_env()
			client.login(
				registry=settings.docker_registry_url,
				username=settings.docker_registry_username,
				password=settings.docker_registry_password,
			)

			client.images.push(self.docker_image_repository, self.docker_image_tag)

			end_time = now()
			step.duration = frappe.utils.rounded((end_time - start_time).total_seconds(), 1)
			step.status = "Success"

			self.save()
			frappe.db.commit()
		except Exception:
			step.status = "Failure"
			self.save()
			frappe.db.commit()
			raise

	def create_deploy(self, staging: bool):
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

	def _create_deploy(self, servers: List[str], staging):
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
		if self.status == "Running":
			frappe.publish_realtime(
				f"bench_deploy:{self.name}:steps", {"steps": self.build_steps}
			)
		else:
			frappe.publish_realtime(f"bench_deploy:{self.name}:finished")


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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Deploy Candidate"
)
