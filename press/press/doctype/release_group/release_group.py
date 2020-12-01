# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class ReleaseGroup(Document):
	def validate(self):
		self.validate_title()
		self.validate_frappe_app()
		self.validate_duplicate_app()
		self.validate_app_versions()

	def on_trash(self):
		candidates = frappe.get_all("Deploy Candidate", {"group": self.name})
		for candidate in candidates:
			frappe.delete_doc("Deploy Candidate", candidate.name)

	def on_update(self):
		self.create_deploy_candidate()

	def validate_title(self):
		if frappe.get_all(
			"Release Group",
			{"title": self.title, "team": self.team or "", "name": ("!=", self.name)},
			limit=1,
		):
			frappe.throw(f"Release Group {self.title} already exists.", frappe.ValidationError)

	def validate_frappe_app(self):
		if self.applications[0].application != "frappe":
			frappe.throw("First application must be Frappe", frappe.ValidationError)

	def validate_duplicate_app(self):
		apps = set()
		for app in self.applications:
			app_name = app.application
			if app_name in apps:
				frappe.throw(
					f"Application {app.application} can be added only once", frappe.ValidationError,
				)
			apps.add(app_name)

	def validate_app_versions(self):
		# Application Source should be compatible with Release Group's version
		for app in self.applications:
			source = frappe.get_doc("Application Source", app.source)
			if all(row.version != self.version for row in source.versions):
				frappe.throw(
					f"Application Source {app.source} version is not {self.version}",
					frappe.ValidationError,
				)

	def create_deploy_candidate(self):
		if not self.enabled:
			return
		releases = []
		for app in self.applications:
			release = frappe.get_all(
				"Application Release",
				fields=["name", "application", "hash"],
				filters={"application": app.application},
				order_by="creation desc",
				limit=1,
			)
			if release:
				release = release[0]
				releases.append(
					{"release": release.name, "application": release.application, "hash": release.hash}
				)
		frappe.get_doc(
			{"doctype": "Deploy Candidate", "group": self.name, "applications": releases}
		).insert()

	def add_application(self, source):
		self.append(
			"applications", {"source": source.name, "application": source.application}
		)
		self.save()


def new_release_group(title, version, applications, team=None):
	group = frappe.get_doc(
		{
			"doctype": "Release Group",
			"title": title,
			"version": version,
			"applications": applications,
			"team": team,
		}
	).insert()
	return group
