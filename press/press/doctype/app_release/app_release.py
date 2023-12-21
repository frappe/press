# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import os
import shlex
import shutil
import subprocess

import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.press.doctype.app_source.app_source import AppSource
from press.utils import log_error


class AppRelease(Document):
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
		try:
			if self.cloned:
				return
			self._set_prepared_clone_directory()
			self._set_code_server_url()
			self._clone_repo()
			self.cloned = True
			self.save(ignore_permissions=True)
		except Exception:
			log_error("App Release Clone Exception", release=self.name)

	def run(self, command):
		try:
			return run(command, self.clone_directory)
		except Exception as e:
			self.cleanup()
			log_error("App Release Command Exception", command=command, output=e.output.decode())
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
		if source.github_installation_id:
			token = get_access_token(source.github_installation_id)
			url = f"https://x-access-token:{token}@github.com/{source.repository_owner}/{source.repository}"
		else:
			url = source.repository_url
		self.output = ""
		self.output += self.run("git init")
		self.output += self.run(f"git checkout -B {source.branch}")
		origin_exists = self.run("git remote").strip() == "origin"
		if origin_exists:
			self.output += self.run(f"git remote set-url origin {url}")
		else:
			self.output += self.run(f"git remote add origin {url}")
		self.output += self.run("git config credential.helper ''")
		self.output += self.run(f"git fetch --depth 1 origin {self.hash}")
		self.output += self.run(f"git checkout {self.hash}")
		self.output += self.run(f"git reset --hard {self.hash}")

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
				log_error("App Release Cleanup Error", release=release)
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


def get_prepared_clone_directory(self, app: str, source: str, hash: str) -> str:
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
	if not os.path.exists(self.clone_directory):
		os.mkdir(clone_directory)

	return clone_directory


def get_changed_files_between_hashes(source, old_hash, new_hash) -> list[str]:
	"""
	Checks diff between two App Releases, if they have not been cloned
	the App Releases are cloned this is because the commit needs to be
	fetched to diff since it happens locally.

	Note: order of passed hashes do not matter.
	"""
	hashes = [old_hash, new_hash]
	releases = frappe.get_list(
		"App Release",
		fields=["cloned", "name", "clone_directory"],
		filters={"source": source, "hash": ["in", hashes]},
	)

	if len(releases) != 2:
		frappe.throw("Invalid number of App Releases found.")

	for release in releases:
		if release["cloned"]:
			continue

		release_doc: AppRelease = frappe.get_doc("App Release", release["name"])
		release_doc._clone()

	old, new = releases
	cwd = old.clone_directory

	run(f"git remote add -f diff_temp {new.clone_directory}", cwd)
	run(f"git fetch --depth 1 diff_temp {new_hash}", cwd)
	diff = run(f"git diff --name-only {old_hash} {new_hash}", cwd)
	run("git remote remove diff_temp", cwd)

	return diff.splitlines()


def run(command, cwd):
	return subprocess.check_output(
		shlex.split(command), stderr=subprocess.STDOUT, cwd=cwd
	).decode()
