# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

import frappe
import requests
from frappe.model.document import Document
from frappe.model.naming import make_autoname

from press.api.github import get_access_token, get_auth_headers
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import get_current_team, log_error

REQUIRED_APPS_PATTERN = re.compile(r"^\s*(?!#)\s*required_apps\s*=\s*\[(.*?)\]", re.DOTALL | re.MULTILINE)

if TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease


class AppSource(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.app_source_version.app_source_version import AppSourceVersion
		from press.press.doctype.required_apps.required_apps import RequiredApps

		app: DF.Link
		app_title: DF.Data
		branch: DF.Data
		enabled: DF.Check
		frappe: DF.Check
		github_installation_id: DF.Data | None
		last_github_poll_failed: DF.Check
		last_github_response: DF.Code | None
		last_synced: DF.Datetime | None
		public: DF.Check
		repository: DF.Data | None
		repository_owner: DF.Data | None
		repository_url: DF.Data
		required_apps: DF.Table[RequiredApps]
		team: DF.Link
		uninstalled: DF.Check
		versions: DF.Table[AppSourceVersion]
	# end: auto-generated types

	dashboard_fields = ("repository_owner", "repository", "branch")

	def set_required_apps(self, match: str):
		# In the format frappe/erpnext
		apps = match.replace("'", "").replace('"', "").replace(" ", "").split(",")
		added_required_apps = [app.repository_url for app in self.required_apps]

		for app in apps:
			try:
				owner, repo = app.split("/")
			except ValueError:
				owner, repo = "frappe", app

			repository_url = f"https://github.com/{owner}/{repo}"
			if repository_url not in added_required_apps:
				self.append("required_apps", {"repository_url": repository_url})

	def validate_dependent_apps(self):
		hooks_uri = f"{self.repository_owner}/{self.repository}/{self.branch}/{self.app}/hooks.py"
		raw_content_url = (
			f"https://{get_access_token(self.github_installation_id)}@raw.githubusercontent.com/"
			if self.github_installation_id
			else "https://raw.githubusercontent.com/"
		)
		uri = raw_content_url + hooks_uri

		try:
			response = requests.get(uri, timeout=10)
			if not response.ok:
				return

			required_apps = REQUIRED_APPS_PATTERN.findall(response.text)
			required_apps = [required_app for required_app in required_apps if required_app]

			if required_apps:
				required_apps = required_apps[0]
				self.set_required_apps(match=required_apps)

		except Exception as e:
			frappe.log_error(f"Error fetching hooks.py: {e}", "App Source Dependency Check")
			return  # Continue with the save process even if validation fails

	def autoname(self):
		series = f"SRC-{self.app}-.###"
		self.name = make_autoname(series)

	def after_insert(self):
		self.create_release()

	def on_update(self):
		self.create_release()

	def validate(self):
		self.validate_source_signature()
		self.validate_duplicate_versions()

	def add_version(self, version):
		self.append("versions", {"version": version})
		self.save()

	def validate_source_signature(self):
		# Don't allow multiple sources with same signature
		if frappe.db.exists(
			"App Source",
			{
				"name": ("!=", self.name),
				"app": self.app,
				"repository_url": self.repository_url,
				"branch": self.branch,
				"team": self.team,
			},
		):
			frappe.throw(
				f"Already added {(self.repository_url, self.branch)} for {self.app}",
				frappe.ValidationError,
			)

	def validate_duplicate_versions(self):
		# Don't allow versions to be added multiple times
		versions = set()
		for row in self.versions:
			if row.version in versions:
				frappe.throw(f"Version {row.version} can be added only once", frappe.ValidationError)
			versions.add(row.version)

	def before_save(self):
		# Assumes repository_url looks like https://github.com/frappe/erpnext
		self.repository_url = self.repository_url.removesuffix(".git")

		_, self.repository_owner, self.repository = self.repository_url.rsplit("/", 2)
		self.validate_dependent_apps()
		# self.create_release()

	@frappe.whitelist()
	def create_release(
		self,
		force: bool = False,
		commit_hash: str | None = None,
	):
		if self.last_github_poll_failed and not force:
			return None

		_commit_hash, commit_info, ok = self.get_commit_info(
			commit_hash,
		)

		if not ok:
			return None

		try:
			return self._create_release(
				_commit_hash,
				commit_info,
			)
		except Exception:
			log_error("Create Release Error", doc=self)

	def _create_release(self, commit_hash: str, commit_info: dict) -> str:
		releases = frappe.get_all(
			"App Release",
			{
				"app": self.app,
				"source": self.name,
				"hash": commit_hash,
			},
			pluck="name",
			limit=1,
		)
		if len(releases) > 0:
			# No need to create a new release
			return releases[0]

		return self.create_release_from_commit_info(
			commit_hash,
			commit_info,
		).name

	def create_release_from_commit_info(
		self,
		commit_hash: str,
		commit_info: dict,
	):
		app_release: "AppRelease" = frappe.get_doc(
			{
				"doctype": "App Release",
				"app": self.app,
				"source": self.name,
				"hash": commit_hash,
				"team": self.team,
				"message": commit_info.get("message"),
				"author": commit_info.get("author", {}).get("name"),
				"timestamp": get_timestamp_from_commit_info(commit_info),
			}
		).insert(ignore_permissions=True)
		return app_release

	def get_commit_info(self, commit_hash: None | str = None) -> tuple[str, dict, bool]:
		"""
		If `commit_hash` is not provided, `commit_info` is of the latest commit
		on the branch pointed to by `self.hash`.
		"""
		if (response := self.poll_github(commit_hash)).ok:
			self.set_poll_succeeded()
		else:
			self.set_poll_failed(response)
			self.db_update()
			return ("", {}, False)

		# Will cause recursion of db.save is used
		self.db_update()

		data = response.json()
		if commit_hash:
			return (commit_hash, data.get("commit", {}), True)

		commit_hash = data.get("commit", {}).get("sha", "")
		commit_info = data.get("commit", {}).get("commit", {})
		return (commit_hash, commit_info, True)

	def poll_github(self, commit_hash: None | str = None) -> requests.Response:
		headers = self.get_auth_headers()
		url = f"https://api.github.com/repos/{self.repository_owner}/{self.repository}"

		if commit_hash:
			# page and per_page set to reduce unnecessary diff info
			url = f"{url}/commits/{commit_hash}?page=1&per_page=1"
		else:
			url = f"{url}/branches/{self.branch}"

		return requests.get(url, headers=headers)

	def set_poll_succeeded(self):
		self.last_github_response = ""
		self.last_github_poll_failed = False
		self.last_synced = frappe.utils.now()
		self.uninstalled = False

	def set_poll_failed(self, response):
		self.last_github_response = response.text or ""
		self.last_github_poll_failed = True
		self.last_synced = frappe.utils.now()

		"""
		If poll fails with 404 after updating the `github_installation_id` it
		*probably* means that FC hasn't been granted access to this particular
		app by the user.

		In this case the App Source is in an uninstalled state.
		"""
		self.uninstalled = response.status_code == 404

		if response.status_code != 404:
			log_error(
				"Create Release Error",
				response_status_code=response.status_code,
				response_text=response.text,
				doc=self,
			)

	def get_auth_headers(self) -> dict:
		return get_auth_headers(self.github_installation_id)

	def get_access_token(self) -> str | None:
		if self.github_installation_id:
			return get_access_token(self.github_installation_id)

		return frappe.get_value("Press Settings", None, "github_access_token")

	def get_repo_url(self) -> str:
		if not self.github_installation_id:
			return self.repository_url

		token = get_access_token(self.github_installation_id)
		if token is None:
			# Do not edit without updating deploy_notifications.py
			raise Exception("App installation token could not be fetched", self.app)

		return f"https://x-access-token:{token}@github.com/{self.repository_owner}/{self.repository}"


def create_app_source(
	app: str, repository_url: str, branch: str, versions: list[str], required_apps: list[str]
) -> AppSource:
	team = get_current_team()

	app_source = frappe.get_doc(
		{
			"doctype": "App Source",
			"app": app,
			"repository_url": repository_url,
			"branch": branch,
			"team": team,
			"versions": [{"version": version} for version in versions],
			"required_apps": [{"repository_url": required_app} for required_app in required_apps],
		}
	)

	app_source.save()

	return app_source


get_permission_query_conditions = get_permission_query_conditions_for_doctype("App Source")


def get_timestamp_from_commit_info(commit_info: dict) -> str | None:
	timestamp_str = commit_info.get("author", {}).get("date")
	if not timestamp_str:
		return None

	timestamp_str = timestamp_str.replace("Z", "+00:00")
	return datetime.fromisoformat(timestamp_str).strftime("%Y-%m-%d %H:%M:%S")
