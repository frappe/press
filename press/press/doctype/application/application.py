# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.utils import log_error
import requests


class Application(Document):
	def on_update(self):
		self.create_app_release()

	def create_app_release(self):
		if not self.enabled:
			return
		try:
			if self.installation:
				token = get_access_token(self.installation)
				headers = {
					"Authorization": f"token {token}",
				}
			else:
				headers = {}
			branch = requests.get(
				f"https://api.github.com/repos/{self.repo_owner}/{self.repo}/branches/{self.branch}",
				headers=headers,
			).json()
			hash = branch["commit"]["sha"]
			if not frappe.db.exists("App Release", {"hash": hash, "app": self.name}):
				is_first_release = frappe.db.count("App Release", {"app": self.name}) == 0
				frappe.get_doc(
					{
						"doctype": "App Release",
						"app": self.name,
						"hash": hash,
						"message": branch["commit"]["commit"]["message"],
						"author": branch["commit"]["commit"]["author"]["name"],
						"deployable": bool(is_first_release),
					}
				).insert()
		except Exception:
			log_error("App Release Creation Error", app=self.name)


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
