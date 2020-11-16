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
		return frappe.get_doc(
			{
				"doctype": "Application Source",
				"application": self.name,
				"version": version,
				"repository_url": repository_url,
				"branch": branch,
				"team": team,
				"github_installation_id": github_installation_id,
				"public": public,
			}
		).insert()

	def before_save(self):
		self.frappe = self.name == "frappe"

	def on_update(self):
		return


def new_application(name, title):
	application = frappe.get_doc(
		{"doctype": "Application", "name": name, "title": title}
	).insert()
	return application


def poll_new_releases():
	for app in frappe.get_all("Application"):
		app = frappe.get_doc("Application", app.name)
		app.create_app_release()


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabApplication`.`team` = {frappe.db.escape(team)})"
