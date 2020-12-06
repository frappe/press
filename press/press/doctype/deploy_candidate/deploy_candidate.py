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

# import json
import regex

import dockerfile
import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import now_datetime as now
from press.utils import log_error
from frappe.core.utils import find
import docker


class DeployCandidate(Document):
	def after_insert(self):
		return

	def build(self):
		self.status = "Pending"
		self.add_build_steps()
		self.save()
		frappe.enqueue_doc(
			self.doctype, self.name, "_build", timeout=1200, enqueue_after_commit=True
		)
		frappe.db.commit()

	def _build(self):
		self.status = "Running"
		self.build_start = now()
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
			("pre", "node", "Setup Prerequisites", "Install Node.js"),
			("pre", "yarn", "Setup Prerequisites", "Install Yarn"),
			("bench", "bench", "Setup Bench", "Install Bench"),
			("bench", "env", "Setup Bench", "Setup Virtual Environment"),
		]

		clone_steps, app_install_steps = [], []
		for application in self.applications:
			application_title = frappe.db.get_value(
				"Application", application.application, "title"
			)
			clone_steps.append(
				("clone", application.application, "Clone Repositories", application_title)
			)

			app_install_steps.append(
				("apps", application.application, "Install Applications", application_title)
			)

		assets_steps = [("assets", "assets", "Build Assets", "Build Assets")]

		steps = clone_steps + preparation_steps + app_install_steps + assets_steps

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
		self.save()

	def _prepare_build_directory(self):
		build_directory = frappe.get_value("Press Settings", None, "build_directory")
		if not os.path.exists(build_directory):
			os.mkdir(build_directory)

		group_directory = os.path.join(build_directory, self.group)
		if not os.path.exists(group_directory):
			os.mkdir(group_directory)

		self.build_directory = os.path.join(build_directory, self.group, self.name)
		if not os.path.exists(self.build_directory):
			os.mkdir(self.build_directory)

	def _prepare_build_context(self):
		# Create apps directory
		apps_directory = os.path.join(self.build_directory, "apps")
		os.mkdir(apps_directory)

		for application in self.applications:
			source, cloned = frappe.db.get_value(
				"Application Release", application.release, ["clone_directory", "cloned"]
			)
			step = find(
				self.build_steps,
				lambda x: x.stage_slug == "clone" and x.step_slug == application.application,
			)
			step.command = f"git clone {application.application}"

			if cloned:
				step.cached = True
				step.status = "Success"
			else:
				step.status = "Running"
				start_time = now()

				self.save()
				frappe.db.commit()

				release = frappe.get_doc("Application Release", application.release)
				release._clone()
				source = release.clone_directory

				end_time = now()
				step.duration = frappe.utils.rounded((end_time - start_time).total_seconds(), 1)
				step.output = release.output
				step.status = "Success"

			target = os.path.join(self.build_directory, "apps", application.application)
			shutil.copytree(source, target)

			self.save()
			frappe.db.commit()

		# Copy Dockerfile
		shutil.copy(
			os.path.join(frappe.get_app_path("press", "docker"), "Dockerfile"),
			self.build_directory,
		)
		shutil.copy(
			os.path.join(frappe.get_app_path("press", "docker"), "common_site_config.json"),
			self.build_directory,
		)

	def _run_docker_build(self):
		environment = os.environ
		environment.update(
			{"DOCKER_BUILDKIT": "1", "BUILDKIT_PROGRESS": "plain", "PROGRESS_NO_TRUNC": "1"}
		)

		self.docker_image_name = self.group
		self.docker_image_tag = self.name
		result = self.run(
			f"docker build -t {self.docker_image_name}:{self.docker_image_tag} .", environment
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

			try:
				# Remove step index from line
				step_index, line = line.split(maxsplit=1)
				step_index = int(step_index[1:])

				# Parse first line and add step to steps dict
				if step_index not in steps and line.startswith("[stage-"):
					name = line.split("]", maxsplit=1)[1].strip()
					match = regex.search("`#stage-(.*)`", name)
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

		image = client.images.get(self.docker_image_id)
		repository = f"{settings.docker_registry_url}/{self.docker_image_name}"
		image.tag(repository, self.docker_image_tag)

		client.images.push(repository, self.docker_image_tag)

	def create_deploy(self):
		try:
			deploy = frappe.db.exists("Deploy", {"group": self.group, "candidate": self.name})
			if deploy:
				return

			deployed_benches = frappe.get_all(
				"Bench", fields=["server"], filters={"group": self.group, "status": "Active"}
			)
			servers = list(set(bench.server for bench in deployed_benches))
			benches = []
			domain = frappe.db.get_single_value("Press Settings", "domain")
			for server in servers:
				server_name = server.replace(f".{domain}", "")
				bench_name = f"bench-{self.group.replace(' ', '-').lower()}-{server_name}"
				bench_name = append_number_if_name_exists("Bench", bench_name, separator="-")
				benches.append({"server": server, "bench_name": bench_name})
				if benches:
					deploy_doc = frappe.get_doc(
						{
							"doctype": "Deploy",
							"group": self.group,
							"candidate": self.name,
							"benches": benches,
						}
					)
					deploy_doc.insert()
		except Exception:
			log_error("Deploy Creation Error", candidate=self.name)


def ansi_escape(text):
	# Reference:
	# https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
	ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
	return ansi_escape.sub("", text)
