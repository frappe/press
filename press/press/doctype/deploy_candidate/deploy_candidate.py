from __future__ import annotations

import contextlib
import json
import os
import re

# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt
import shlex
import subprocess
import typing
from datetime import datetime, timedelta
from subprocess import Popen
from typing import Literal

import frappe
import semantic_version
from frappe.core.utils import find
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import now_datetime as now
from frappe.utils import rounded

from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.app_release.app_release import (
	AppReleasePair,
	get_changed_files_between_hashes,
)
from press.press.doctype.deploy_candidate.utils import (
	PackageManagerFiles,
	is_suspended,
)
from press.press.doctype.release_group.release_group import DEFAULT_DEPENDENCIES
from press.utils import log_error

# build_duration, pending_duration are Time fields, >= 1 day is invalid
MAX_DURATION = timedelta(hours=23, minutes=59, seconds=59)
TRANSITORY_STATES = ["Scheduled", "Pending", "Preparing", "Running"]
RESTING_STATES = ["Draft", "Success", "Failure"]

DISTUTILS_SUPPORTED_VERSION = semantic_version.SimpleSpec("<3.12")

if typing.TYPE_CHECKING:
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild
	from press.press.doctype.release_group.release_group import ReleaseGroup


class DeployCandidate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.deploy_candidate_app.deploy_candidate_app import DeployCandidateApp
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
		arm_build: DF.Link | None
		build_token: DF.Data | None
		compress_app_cache: DF.Check
		dependencies: DF.Table[DeployCandidateDependency]
		environment_variables: DF.Table[DeployCandidateVariable]
		group: DF.Link
		gunicorn_threads_per_worker: DF.Int
		intel_build: DF.Link | None
		is_redisearch_enabled: DF.Check
		merge_all_rq_queues: DF.Check
		merge_default_and_short_rq_queues: DF.Check
		packages: DF.Table[DeployCandidatePackage]
		redis_cache_size: DF.Int
		requires_arm_build: DF.Check
		requires_intel_build: DF.Check
		team: DF.Link
		use_app_cache: DF.Check
		use_rq_workerpool: DF.Check
		user_certificate: DF.Code | None
		user_private_key: DF.Code | None
		user_public_key: DF.Code | None
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
		"apps",
		"group",
		"retry_count",
	)

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
		def get_job_duration_in_seconds(duration):
			if not duration:
				return 0
			return f"{float(rounded(duration.total_seconds(), 2))}s"

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
				doc.jobs.append(
					{
						**job[0],
						"title": f"Deploying {bench.bench}",
						"duration": get_job_duration_in_seconds(getattr(job[0], "duration", 0)) if job else 0,
					}
				)

		# if any job is in running, pending state, set the status to deploying
		if any(job.get("status") in ["Running", "Pending"] for job in doc.jobs):
			doc.status = "Deploying"

	def autoname(self):
		group = self.group[6:]
		series = f"deploy-{group}-.######"
		self.name = make_autoname(series)

	def on_trash(self):
		frappe.db.delete(
			"Press Notification",
			{"document_type": self.doctype, "document_name": self.name},
		)

	@property
	def release_group(self) -> ReleaseGroup:
		return frappe.get_doc("Release Group", self.group)

	@property
	def custom_workers_group(self) -> str:
		custom_workers = self.custom_workers.keys()
		if custom_workers:
			return ",".join(f"frappe-bench-{worker_name}-worker" for worker_name in custom_workers)
		return ""

	@property
	def custom_workers(self):
		if self.release_group.common_site_config:
			common_site_config = json.loads(self.release_group.common_site_config) or frappe._dict()
			return common_site_config.get("workers", frappe._dict())
		return frappe._dict()

	def get_unpublished_marketplace_releases(self) -> list[str]:
		marketplace_app_sources = self.release_group.get_marketplace_app_sources()

		if not marketplace_app_sources:
			return []

		# Marketplace App Releases in this deploy candidate
		dc_app_releases = frappe.get_all(
			"Deploy Candidate App",
			filters={"parent": self.name, "source": ("in", marketplace_app_sources)},
			pluck="release",
		)

		# Unapproved app releases for marketplace apps
		return frappe.get_all(
			"App Release",
			filters={"name": ("in", dc_app_releases), "status": ("!=", "Approved")},
			pluck="name",
		)

	def create_build(self, **kwargs) -> DeployCandidateBuild:
		servers = [server_ref.server for server_ref in self.release_group.servers]

		if frappe.get_value("Server", {"name": ("in", servers)}, "stop_deployments"):
			frappe.throw("Deployments on this server are currently halted!")

		kwargs.update(
			{"doctype": "Deploy Candidate Build", "deploy_candidate": self.name},
		)
		return frappe.get_doc(kwargs)

	@frappe.whitelist()
	def build(
		self,
		no_push: bool = False,
		no_build: bool = False,
		no_cache: bool = False,
	):
		if no_build:
			return None

		deploy_candidate_build = self.create_build(
			no_build=no_build,
			no_push=no_push,
			no_cache=no_cache,
		)
		deploy_candidate_build.insert()
		return dict(error=False, message=deploy_candidate_build.name)

	@frappe.whitelist()
	def schedule_build_and_deploy(
		self,
		run_now: bool = True,
		scheduled_time: datetime | None = None,
		retry_count: int = 0,
	):
		if run_now and not is_suspended():
			return {"error": False, "name": self.build_and_deploy()}

		deploy_candidate_build = self.create_build(
			no_cache=False,
			deploy_after_build=True,
			status="Scheduled",
			scheduled_time=scheduled_time or now(),
			retry_count=retry_count,
		)
		deploy_candidate_build.insert()
		return {"error": False, "name": deploy_candidate_build.name}

	def build_and_deploy(self, no_cache: bool = False) -> str:
		deploy_candidate_build = self.create_build(no_cache=no_cache, deploy_after_build=True)
		deploy_candidate_build.insert()
		return deploy_candidate_build.name

	def _set_app_cached_flags(self) -> None:
		for app in self.apps:
			app.use_cached = bool(self.use_app_cache)

	def _update_app_releases(self) -> None:
		if not frappe.get_value("Release Group", self.group, "use_delta_builds"):
			return

		try:
			update = self.get_pull_update_dict()
		except Exception:
			log_error(title="Failed to get Pull Update Dict", doc=self)
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

	def run(self, command, environment=None, directory=None):
		process = Popen(
			shlex.split(command),
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			env=environment,
			cwd=directory,
			universal_newlines=True,
		)
		yield from process.stdout
		process.stdout.close()
		return_code = process.wait()
		if return_code:
			raise subprocess.CalledProcessError(return_code, command)

	def generate_ssh_keys(self, build_directory: str):
		ca = frappe.db.get_single_value("Press Settings", "ssh_certificate_authority")
		if not ca:
			return

		ca = frappe.get_doc("SSH Certificate Authority", ca)
		ssh_directory = os.path.join(build_directory, "config", "ssh")

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

		self.save(ignore_permissions=True)
		# Remove user key files
		os.remove(user_private_key_path)
		os.remove(user_public_key_path)
		os.remove(user_certificate_path)

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
				p = p.strip()
				if p in existing_apt_packages:
					continue
				existing_apt_packages.add(p)
				app_packages.append(p)

			if not app_packages:
				continue

			self._add_packages(app_packages)

	def __prepare_chunks(self, packages: list[str]):
		"""Chunk packages into groups of 140 characters"""
		# Start with one empty chunk
		chunks: list[list[str]] = [[]]
		for package in packages:
			# Appending the package to the last chunk will keep it under 140
			# Append package to last chunk
			if len(" ".join(chunks[-1] + [package])) < 140:
				chunks[-1].append(package)
			# Appending the package to the last chunk will make it larger than 140
			# Add package in a new chunk
			else:
				if len(package) > 140:
					raise frappe.ValidationError(
						f"Package {package} is too long to be added to the Dockerfile"
					)
				chunks.append([package])
		return chunks

	def _add_packages(self, packages: list[str]):
		for chunk in self.__prepare_chunks(packages):
			package = dict(package_manager="apt", package=" ".join(chunk))
			self.append("packages", package)

	def _set_additional_packages(self):
		"""
		additional_packages is used when rendering the Dockerfile template
		"""
		self.additional_packages = []
		dep_versions = {d.dependency: d.version for d in self.dependencies}
		for p in self.packages:
			#  second clause cause: '/opt/certbot/bin/pip'
			if p.package_manager not in ["apt", "pip"] and not p.package_manager.endswith("/pip"):
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

	def get_certificate(self):
		return {
			"id_rsa": self.user_private_key,
			"id_rsa.pub": self.user_public_key,
			"id_rsa-cert.pub": self.user_certificate,
		}

	def get_dependency_version(self, dependency: str, as_env: bool = False):
		if dependency.islower():
			dependency = dependency.upper() + "_VERSION"

		dependency_record = find(self.dependencies, lambda x: x.dependency == dependency)
		if not dependency_record:
			version = find(DEFAULT_DEPENDENCIES, lambda x: x["dependency"] == dependency)["version"]
		else:
			version = dependency_record.version

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
		benches = frappe.get_all("Bench", filters={"group": self.group, "status": "Active"}, limit=1)
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

	def get_duplicate_dc(self) -> "DeployCandidate | None":
		if not (dc := self.release_group.create_deploy_candidate()):
			return None

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

	def has_app(self, name: str) -> bool:
		org = None
		if "/" in name:
			org, name = name.split("/", maxsplit=1)

		for app in self.apps:
			if app.app != name:
				continue

			if org is None:
				return True

			owner = frappe.db.get_value(
				"App Source",
				app.source,
				"repository_owner",
			)
			return owner == org
		return False

	def _fail_site_group_deploy_if_exists(self):
		site_group_deploy = frappe.db.get_value(
			"Site Group Deploy",
			{
				"release_group": self.group,
				"site": ("is", "not set"),
				"bench": ("is", "not set"),
			},
		)
		if site_group_deploy:
			frappe.db.set_value("Site Group Deploy", site_group_deploy, "status", "Bench Deploy Failed")


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

		if "/www/" in file_path:
			return True

		# Probably requires build
		return False

	return True


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


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Deploy Candidate")


@frappe.whitelist()
def toggle_builds(suspend):
	frappe.only_for("System Manager")
	frappe.db.set_single_value("Press Settings", "suspend_builds", suspend)


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
		if app_titles:
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
