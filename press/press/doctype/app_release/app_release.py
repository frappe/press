# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import os
import shlex
import shutil
import subprocess
from datetime import datetime
from typing import Optional, TypedDict

import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.press.doctype.app_source.app_source import AppSource
from press.utils import log_error

AppReleaseDict = TypedDict(
	"AppReleaseDict",
	name=str,
	source=str,
	hash=str,
	cloned=int,
	clone_directory=str,
	timestamp=Optional[datetime],
	creation=datetime,
)
AppReleasePair = TypedDict(
	"AppReleasePair",
	old=AppReleaseDict,
	new=AppReleaseDict,
)


class AppRelease(Document):
	dashboard_fields = ["app", "source", "message", "hash", "author", "status"]

	def validate(self):
		if not self.clone_directory:
			self.set_clone_directory()

	def before_save(self):
		apps = frappe.get_all("Featured App", {"parent": "Marketplace Settings"}, pluck="app")
		teams = frappe.get_all(
			"Auto Release Team", {"parent": "Marketplace Settings"}, pluck="team"
		)
		if self.team in teams or self.app in apps:
			self.status = "Approved"

	def after_insert(self):
		self.publish_created()
		self.create_release_differences()
		self.auto_deploy()

	def publish_created(self):
		frappe.publish_realtime(
			event="new_app_release_created", message={"source": self.source}
		)

	def get_source(self) -> AppSource:
		"""Return the `App Source` associated with this `App Release`"""
		return frappe.get_doc("App Source", self.source)

	def get_commit_link(self) -> str:
		"""Return the commit URL for this app release"""
		return f"{self.get_source().repository_url}/commit/{self.hash}"

	@frappe.whitelist()
	def clone(self):
		frappe.enqueue_doc(self.doctype, self.name, "_clone")

	def _clone(self):
		if self.cloned:
			return

		self._set_prepared_clone_directory()
		self._set_code_server_url()
		self._clone_repo()
		self.cloned = True
		self.save(ignore_permissions=True)

	def run(self, command):
		try:
			return run(command, self.clone_directory)
		except Exception as e:
			self.cleanup()
			log_error(
				"App Release Command Exception",
				command=command,
				output=e.output.decode(),
				reference_doctype="App Release",
				reference_name=self.name,
			)
			raise e

	def set_clone_directory(self):
		clone_directory = frappe.db.get_single_value("Press Settings", "clone_directory")
		self.clone_directory = os.path.join(
			clone_directory, self.app, self.source, self.hash[:10]
		)

	def _set_prepared_clone_directory(self):
		self.clone_directory = get_prepared_clone_directory(self.app, self.source, self.hash)

	def _set_code_server_url(self) -> None:
		code_server = frappe.db.get_single_value("Press Settings", "code_server")
		code_server_url = f"{code_server}/?folder=/home/coder/project/{self.app}/{self.source}/{self.hash[:10]}"
		self.code_server_url = code_server_url

	def _clone_repo(self):
		source = frappe.get_doc("App Source", self.source)
		url = self._get_repo_url(source)

		self.output = ""
		self.output += self.run("git init")
		self.output += self.run(f"git checkout -B {source.branch}")
		origin_exists = self.run("git remote").strip() == "origin"
		if origin_exists:
			self.output += self.run(f"git remote set-url origin {url}")
		else:
			self.output += self.run(f"git remote add origin {url}")
		self.output += self.run("git config credential.helper ''")

		try:
			self.output += self.run(f"git fetch --depth 1 origin {self.hash}")
		except subprocess.CalledProcessError as e:
			stdout = e.stdout.decode("utf-8")
			if "Repository not found." not in stdout:
				raise e

			# Do not edit without updating deploy_notifications.py
			raise Exception("Repository could not be fetched", self.app)

		self.output += self.run(f"git checkout {self.hash}")
		self.output += self.run(f"git reset --hard {self.hash}")

	def _get_repo_url(self, source: "AppSource") -> str:
		if not source.github_installation_id:
			return source.repository_url

		token = get_access_token(source.github_installation_id)
		if token is None:
			# Do not edit without updating deploy_notifications.py
			raise Exception("App installation token could not be fetched", self.app)

		return f"https://x-access-token:{token}@github.com/{source.repository_owner}/{source.repository}"

	def on_trash(self):
		if self.clone_directory and os.path.exists(self.clone_directory):
			shutil.rmtree(self.clone_directory)

	@frappe.whitelist()
	def cleanup(self):
		self.on_trash()
		self.cloned = False
		self.save(ignore_permissions=True)

	def create_release_differences(self):
		releases = frappe.db.sql(
			"""
			SELECT
				DISTINCT(app.release)
			FROM
				`tabBench` bench
			LEFT JOIN
				`tabBench App` app
			ON
				bench.name = app.parent
			WHERE
				bench.status != "Archived" AND
				app.source = %s AND
				app.release != %s
		""",
			(self.source, self.name),
			as_dict=True,
		)
		for release in releases:
			difference = frappe.get_doc(
				{
					"doctype": "App Release Difference",
					"app": self.app,
					"source": self.source,
					"source_release": release.release,
					"destination_release": self.name,
				}
			)
			difference.insert()

	def auto_deploy(self):
		groups = frappe.get_all(
			"Release Group App",
			["parent"],
			{"source": self.source, "enable_auto_deploy": True},
		)
		for group in groups:
			if frappe.get_all(
				"Deploy Candidate",
				{"status": ("in", ("Pending", "Running")), "group": group.parent},
			):
				continue
			group = frappe.get_doc("Release Group", group.parent)
			apps = [app.as_dict() for app in group.apps if app.enable_auto_deploy]
			candidate = group.create_deploy_candidate(apps)
			if candidate:
				candidate.deploy_to_production()


def cleanup_unused_releases():
	sources = frappe.get_all(
		"App Release",
		fields=["source as name", "count(*) as count"],
		filters={"cloned": True},
		order_by="count desc",
		group_by="source",
	)
	active_releases = set(
		release.release
		for release in frappe.get_all(
			"Bench",
			fields=["`tabBench App`.release"],
			filters={"status": ("!=", "Archived")},
		)
	)

	deleted = 0
	for source in sources:
		releases = frappe.get_all(
			"App Release",
			{"source": source.name, "cloned": True},
			pluck="name",
			order_by="creation ASC",
		)
		for index, release in enumerate(releases):

			if deleted > 2000:
				return

			# Skip the most recent release
			if index >= len(releases) - 1:
				break

			# Skip already deployed releases
			if release in active_releases:
				continue

			try:
				frappe.get_doc("App Release", release, for_update=True).cleanup()
				deleted += 1
				frappe.db.commit()
			except Exception:
				log_error(
					"App Release Cleanup Error",
					release=release,
					reference_doctype="App Release",
					reference_name=release,
				)
				frappe.db.rollback()


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return ""

	team = get_current_team()

	return (
		f"(`tabApp Release`.`team` = {frappe.db.escape(team)} or `tabApp"
		" Release`.`public` = 1)"
	)


def has_permission(doc, ptype, user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	user_type = frappe.db.get_value("User", user, "user_type", cache=True)
	if user_type == "System User":
		return True

	team = get_current_team()
	if doc.public or doc.team == team:
		return True

	return False


def get_prepared_clone_directory(app: str, source: str, hash: str) -> str:
	clone_directory: str = frappe.db.get_single_value("Press Settings", "clone_directory")
	if not os.path.exists(clone_directory):
		os.mkdir(clone_directory)

	app_directory = os.path.join(clone_directory, app)
	if not os.path.exists(app_directory):
		os.mkdir(app_directory)

	source_directory = os.path.join(app_directory, source)
	if not os.path.exists(source_directory):
		os.mkdir(source_directory)

	clone_directory = os.path.join(clone_directory, app, source, hash[:10])
	if not os.path.exists(clone_directory):
		os.mkdir(clone_directory)

	return clone_directory


def get_changed_files_between_hashes(
	source: str, deployed_hash: str, update_hash: str
) -> Optional[tuple[list[str], AppReleasePair]]:
	"""
	Checks diff between two App Releases, if they have not been cloned
	the App Releases are cloned this is because the commit needs to be
	fetched to diff since it happens locally.

	Note: order of passed hashes do not matter.
	"""
	deployed_release = get_release_by_source_and_hash(source, deployed_hash)
	update_release = get_release_by_source_and_hash(source, update_hash)
	is_valid = is_update_after_deployed(update_release, deployed_release)
	if not is_valid:
		return None

	for release in [deployed_release, update_release]:
		if release["cloned"]:
			continue

		release_doc: AppRelease = frappe.get_doc("App Release", release["name"])
		release_doc._clone()

	cwd = deployed_release["clone_directory"]

	"""
	Setting remote and fetching alters .git contents, hence it has to be
	restored to before the commands had been run. Without this layer will
	be rebuilt.
	"""

	# Save repo state
	run("cp -r .git .git.bak", cwd)

	# Calculate diff against local remote
	run(f"git remote add -f diff_temp {update_release['clone_directory']}", cwd)
	run(f"git fetch --depth 1 diff_temp {update_hash}", cwd)
	diff = run(f"git diff --name-only {deployed_hash} {update_hash}", cwd)

	# Restore repo state
	run("rm -rf .git", cwd)
	run("mv .git.bak .git", cwd)

	return diff.splitlines(), dict(old=deployed_release, new=update_release)


def get_release_by_source_and_hash(source: str, hash: str) -> AppReleaseDict:
	releases: list[AppReleaseDict] = frappe.get_all(
		"App Release",
		filters={"hash": hash, "source": source},
		fields=[
			"name",
			"source",
			"hash",
			"cloned",
			"clone_directory",
			"timestamp",
			"creation",
		],
		limit=1,
	)

	if not releases:
		frappe.throw(f"App Release not found with source: {source} and hash: {hash}")

	return releases[0]


def is_update_after_deployed(
	update_release: AppReleaseDict, deployed_release: AppReleaseDict
) -> bool:
	update_timestamp = update_release["timestamp"]
	deployed_timestamp = deployed_release["timestamp"]
	if update_timestamp and deployed_timestamp:
		return update_timestamp > deployed_timestamp

	return update_release["creation"] > deployed_release["creation"]


def run(command, cwd):
	return subprocess.check_output(
		shlex.split(command), stderr=subprocess.STDOUT, cwd=cwd
	).decode()
