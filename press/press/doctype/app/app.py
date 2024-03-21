# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe
import typing
from frappe.model.document import Document

if typing.TYPE_CHECKING:
	from press.press.doctype.app_source.app_source import AppSource


class App(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		branch: DF.Data | None
		enable_auto_deploy: DF.Check
		enabled: DF.Check
		frappe: DF.Check
		installation: DF.Data | None
		public: DF.Check
		repo: DF.Data | None
		repo_owner: DF.Data | None
		scrubbed: DF.Data | None
		skip_review: DF.Check
		team: DF.Link | None
		title: DF.Data
		url: DF.Data | None
	# end: auto-generated types

	dashboard_fields = ["title"]

	def add_source(
		self,
		version,
		repository_url,
		branch,
		team=None,
		github_installation_id=None,
		public=False,
		repository_owner=None,
	) -> "AppSource":
		existing_source = frappe.get_all(
			"App Source",
			{"app": self.name, "repository_url": repository_url, "branch": branch, "team": team},
			limit=1,
		)
		if existing_source:
			source = frappe.get_doc("App Source", existing_source[0].name)
			versions = set(version.version for version in source.versions)
			if version not in versions:
				source.add_version(version)
		else:
			# Add new App Source
			source = frappe.get_doc(
				{
					"doctype": "App Source",
					"app": self.name,
					"versions": [{"version": version}],
					"repository_url": repository_url,
					"branch": branch,
					"team": team,
					"github_installation_id": github_installation_id,
					"public": public,
					"repository_owner": repository_owner,
				}
			).insert()
		return source

	def before_save(self):
		self.frappe = self.name == "frappe"


def new_app(name, title):
	app = frappe.get_doc({"doctype": "App", "name": name, "title": title}).insert()
	return app


def poll_new_releases():
	for source in frappe.get_all(
		"App Source",
		{"enabled": True, "last_github_poll_failed": False},
		order_by="last_synced",
	):
		try:
			source = frappe.get_doc("App Source", source.name)
			source.create_release()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
