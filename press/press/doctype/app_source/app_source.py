# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from press.api.github import get_access_token
from press.utils import log_error
import requests
from frappe.model.naming import make_autoname


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
					f"Version {row.version} can be added only once", frappe.ValidationError,
				)
			versions.add(row.version)

	def before_save(self):
		# Assumes repository_url looks like https://github.com/frappe/erpnext
		_, self.repository_owner, self.repository = self.repository_url.rsplit("/", 2)
		# self.create_release()

	def create_release(self):
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
			branch = requests.get(
				f"https://api.github.com/repos/{self.repository_owner}/{self.repository}/branches/{self.branch}",
				headers=headers,
			).json()
			hash = branch["commit"]["sha"]
			if not frappe.db.exists(
				"App Release", {"app": self.app, "source": self.name, "hash": hash},
			):
				is_first_release = 0  # frappe.db.count("App Release", {"app": self.name}) == 0
				frappe.get_doc(
					{
						"doctype": "App Release",
						"app": self.app,
						"source": self.name,
						"hash": hash,
						"message": branch["commit"]["commit"]["message"],
						"author": branch["commit"]["commit"]["author"]["name"],
						"deployable": bool(is_first_release),
					}
				).insert()
		except Exception:
			log_error("App Release Creation Error", app=self.name)


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return ""

	team = get_current_team()

	return (
		f"(`tabApp Source`.`team` = {frappe.db.escape(team)} or `tabApp Source`.`public` = 1)"
	)


def has_permission(doc, ptype, user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return True

	team = get_current_team()
	# Don't allow writing to public App Sources
	if ptype == "write":
		if doc.team == team:
			return True
	else:
		if doc.team == team or doc.public:
			return True

	return False
