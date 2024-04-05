# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from datetime import datetime
from typing import List, Optional

import frappe
import requests
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.api.github import get_access_token
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import get_current_team, log_error


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

	@frappe.whitelist()
	def create_release(self, force=False):
		if self.last_github_poll_failed and not force:
			return

		if not (response := self.poll_github_for_branch_info()):
			return

		try:
			self.create_release_from_branch_info(response)
		except Exception:
			log_error("Create Release Error", doc=self)

	def create_release_from_branch_info(self, response):
		response_data = response.json()
		hash = response_data["commit"]["sha"]
		if frappe.db.exists(
			"App Release", {"app": self.app, "source": self.name, "hash": hash}
		):
			# No need to create a new release
			return

		timestamp_str = response_data["commit"]["commit"]["author"]["date"].replace(
			"Z", "+00:00"
		)
		timestamp = datetime.fromisoformat(timestamp_str).strftime("%Y-%m-%d %H:%M:%S")
		is_first_release = 0  # frappe.db.count("App Release", {"app": self.name}) == 0
		frappe.get_doc(
			{
				"doctype": "App Release",
				"app": self.app,
				"source": self.name,
				"hash": hash,
				"team": self.team,
				"message": response_data["commit"]["commit"]["message"],
				"author": response_data["commit"]["commit"]["author"]["name"],
				"timestamp": timestamp,
				"deployable": bool(is_first_release),
			}
		).insert()

	def poll_github_for_branch_info(self):
		headers = self.get_auth_headers()
		response = requests.get(
			f"https://api.github.com/repos/{self.repository_owner}/{self.repository}/branches/{self.branch}",
			headers=headers,
		)

		if not response.ok:
			self.set_poll_failed(response.text)
			log_error(
				"Create Release Error",
				response_status_code=response.status_code,
				response_text=response.text,
				doc=self,
			)
			return

		self.set_poll_succeeded()
		return response

	def set_poll_succeeded(self):
		frappe.db.set_value(
			"App Source",
			self.name,
			{
				"last_github_response": "",
				"last_github_poll_failed": False,
				"last_synced": frappe.utils.now(),
			},
		)

	def set_poll_failed(self, response_text: str):
		pass
		frappe.db.set_value(
			"App Source",
			self.name,
			{
				"last_github_response": response_text or "",
				"last_github_poll_failed": True,
				"last_synced": frappe.utils.now(),
			},
		)

	def get_auth_headers(self) -> dict:
		token = self.get_access_token()
		if not token:
			return {}

		return {"Authorization": f"token {token}"}

	def get_access_token(self) -> Optional[str]:
		if self.github_installation_id:
			return get_access_token(self.github_installation_id)

		return frappe.get_value("Press Settings", None, "github_access_token")


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
