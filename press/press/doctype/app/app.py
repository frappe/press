# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class App(Document):
	def add_source(
		self,
		version,
		repository_url,
		branch,
		team=None,
		github_installation_id=None,
		public=False,
	):
		existing_source = frappe.get_all(
			"App Source",
			{"app": self.name, "repository_url": repository_url, "branch": branch},
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
				}
			).insert()
		return source

	def before_save(self):
		self.frappe = self.name == "frappe"


def new_app(name, title):
	app = frappe.get_doc({"doctype": "App", "name": name, "title": title}).insert()
	return app


def poll_new_releases():
	for source in frappe.get_all("App Source", {"enabled": True}):
		source = frappe.get_doc("App Source", source.name)
		source.create_release()
