# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class Application(Document):
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
			"Application Source",
			{"application": self.name, "repository_url": repository_url, "branch": branch},
			limit=1,
		)
		if existing_source:
			source = frappe.get_doc("Application Source", existing_source[0].name)
			source.add_version(version)
		else:
			# Add new Application Source
			source = frappe.get_doc(
				{
					"doctype": "Application Source",
					"application": self.name,
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


def new_application(name, title):
	application = frappe.get_doc(
		{"doctype": "Application", "name": name, "title": title}
	).insert()
	return application


def poll_new_releases():
	for app in frappe.get_all("Application"):
		app = frappe.get_doc("Application", app.name)
		app.create_app_release()
