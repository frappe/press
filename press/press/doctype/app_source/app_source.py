# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import frappe
import requests
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.api.github import get_access_token, get_auth_headers
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import get_current_team, log_error

if TYPE_CHECKING:
	from press.press.doctype.app_release.app_release import AppRelease


class AppSource(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.app_source_version.app_source_version import AppSourceVersion

		app: DF.Link
		app_title: DF.Data
		branch: DF.Data
		enabled: DF.Check
		frappe: DF.Check
		github_installation_id: DF.Data | None
		gitlab_access_token: DF.Password | None
		gitlab_project_id: DF.Data | None
		last_github_poll_failed: DF.Check
		last_github_response: DF.Code | None
		last_synced: DF.Datetime | None
		public: DF.Check
		repository: DF.Data | None
		repository_owner: DF.Data | None
		repository_url: DF.Data
		team: DF.Link
		uninstalled: DF.Check
		versions: DF.Table[AppSourceVersion]
	# end: auto-generated types

	dashboard_fields = ["repository_owner", "repository", "branch"]

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
				frappe.throw(
					f"Version {row.version} can be added only once", frappe.ValidationError
				)
			versions.add(row.version)

	def before_save(self):
		# Assumes repository_url looks like https://github.com/frappe/erpnext
		self.repository_url = self.repository_url.removesuffix(".git")

		_, self.repository_owner, self.repository = self.repository_url.rsplit("/", 2)
		# self.create_release()

	def create_gitlab_release(self, force=False):
		from urllib.parse import urlparse

		repo_url = urlparse(self.repository_url)
		api_path = (
			f"/api/v4/projects/{self.gitlab_project_id}/repository/branches/{self.branch}"
		)
		url = f"{repo_url.scheme}://{repo_url.netloc}{api_path}"

		headers = {}

		gitlab_token = ""
		if self.get("gitlab_access_token"):
			gitlab_token = gitlab_token or self.get_password("gitlab_access_token")

		if gitlab_token:
			headers["Authorization"] = f"Bearer {gitlab_token}"

		res = requests.get(url, headers=headers).json()

		frappe.db.set_value(
			"App Source",
			self.name,
			{
				"last_github_response": "GitLab",
				"last_github_poll_failed": False,
				"last_synced": frappe.utils.now(),
			},
		)
		commit_hash = res["commit"]["id"]
		commit_message = res["commit"]["message"]
		commit_author = res["commit"]["author_name"]
		if not frappe.db.exists(
			"App Release", {"app": self.app, "source": self.name, "hash": commit_hash}
		):
			frappe.get_doc(
				{
					"doctype": "App Release",
					"app": self.app,
					"source": self.name,
					"hash": commit_hash,
					"team": self.team,
					"message": commit_message,
					"author": commit_author,
					"deployable": False,
				}
			).insert(set_name=f"{self.name}-{commit_hash}")

	@frappe.whitelist()
	def create_release(
		self,
		force: bool = False,
		commit_hash: str | None = None,
	):
		if self.gitlab_project_id:
			self.create_gitlab_release(force)
			return

		if self.last_github_poll_failed and not force:
			return

		_commit_hash, commit_info, ok = self.get_commit_info(
			commit_hash,
		)

		if not ok:
			return

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

	def get_access_token(self) -> Optional[str]:
		if self.github_installation_id:
			return get_access_token(self.github_installation_id)

		return frappe.get_value("Press Settings", None, "github_access_token")

	def get_repo_url(self) -> str:
		if self.get("gitlab_access_token"):
			return self.repository_url.replace(
				"https://", f"https://oauth2:{self.get_password('gitlab_access_token')}@"
			)

		if not self.github_installation_id:
			return self.repository_url

		token = get_access_token(self.github_installation_id)
		if token is None:
			# Do not edit without updating deploy_notifications.py
			raise Exception("App installation token could not be fetched", self.app)

		return f"https://x-access-token:{token}@github.com/{self.repository_owner}/{self.repository}"


def create_app_source(
	app: str, repository_url: str, branch: str, versions: List[str]
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
		}
	)

	app_source.save()

	return app_source


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"App Source"
)


def get_timestamp_from_commit_info(commit_info: dict) -> str | None:
	timestamp_str = commit_info.get("author", {}).get("date")
	if not timestamp_str:
		return None

	timestamp_str = timestamp_str.replace("Z", "+00:00")
	return datetime.fromisoformat(timestamp_str).strftime("%Y-%m-%d %H:%M:%S")
