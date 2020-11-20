# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document
from frappe.core.utils import find


class ReleaseGroup(Document):
	def validate(self):
		self.validate_title()
		self.validate_frappe_app()
		self.validate_duplicate_app()
		self.validate_app_versions()

	def after_insert(self):
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
		source_names = [app.source for app in self.applications]
		sources = frappe.get_all(
			"Application Source", ["name", "version"], {"name": ("in", source_names)}
		)
		for app in self.applications:
			source = find(sources, lambda x: x.name == app.source)
			if source.version != self.version:
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
				fields=["name", "app", "hash"],
				filters={"app": app.application},
				order_by="creation desc",
				limit=1,
			)
			if release:
				release = release[0]
				releases.append({"release": release.name, "app": release.app, "hash": release.hash})
		frappe.get_doc(
			{"doctype": "Deploy Candidate", "group": self.name, "apps": releases}
		).insert()

	def add_app(self, source):
		self.append(
			"applications", {"source": source.name, "application": source.application}
		)


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
