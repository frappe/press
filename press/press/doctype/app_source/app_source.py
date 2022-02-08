# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests

from typing import List
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from press.api.github import get_access_token
from press.utils import log_error, get_current_team
from press.overrides import get_permission_query_conditions_for_doctype


class AppSource(Document):
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
			},
		):
			frappe.throw(
				f"Alread added {(self.repository_url, self.branch)} for {self.app}",
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
		_, self.repository_owner, self.repository = self.repository_url.rsplit("/", 2)
		# self.create_release()

	@frappe.whitelist()
	def create_release(self):
		github_response = None
		try:
			token = None
			if self.github_installation_id:
				token = get_access_token(self.github_installation_id)
			else:
				token = frappe.get_value("Press Settings", None, "github_access_token")

			if token:
				headers = {
					"Authorization": f"token {token}",
				}
			else:
				headers = {}

			github_response = requests.get(
				f"https://api.github.com/repos/{self.repository_owner}/{self.repository}/branches/{self.branch}",
				headers=headers,
			)

			branch = github_response.json()
			hash = branch["commit"]["sha"]
			if not frappe.db.exists(
				"App Release", {"app": self.app, "source": self.name, "hash": hash}
			):
				is_first_release = 0  # frappe.db.count("App Release", {"app": self.name}) == 0
				frappe.get_doc(
					{
						"doctype": "App Release",
						"app": self.app,
						"source": self.name,
						"hash": hash,
						"team": self.team,
						"message": branch["commit"]["commit"]["message"],
						"author": branch["commit"]["commit"]["author"]["name"],
						"deployable": bool(is_first_release),
					}
				).insert()
			frappe.db.set_value(
				"App Source",
				self.name,
				{"last_github_response": "", "last_github_poll_failed": False},
			)
		except Exception:
			github_response = github_response.text if (github_response is not None) else None
			frappe.db.set_value(
				"App Source",
				self.name,
				{"last_github_response": github_response, "last_github_poll_failed": True},
			)
			log_error(
				"App Release Creation Error", app=self.name, github_response=github_response
			)


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
