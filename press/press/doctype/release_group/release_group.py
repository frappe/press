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
		self.validate_servers()

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
		if self.apps[0].app != "frappe":
			frappe.throw("First app must be Frappe", frappe.ValidationError)

	def validate_duplicate_app(self):
		apps = set()
		for app in self.apps:
			app_name = app.app
			if app_name in apps:
				frappe.throw(
					f"App {app.app} can be added only once", frappe.ValidationError,
				)
			apps.add(app_name)

	def validate_app_versions(self):
		# App Source should be compatible with Release Group's version
		for app in self.apps:
			source = frappe.get_doc("App Source", app.source)
			if all(row.version != self.version for row in source.versions):
				frappe.throw(
					f"App Source {app.source} version is not {self.version}", frappe.ValidationError,
				)

	def validate_servers(self):
		if self.servers:
			servers = set(server.server for server in self.servers)
			if len(servers) != len(self.servers):
				frappe.throw(
					"Servers can be added only once", frappe.ValidationError,
				)
		else:
			servers_for_new_bench = frappe.get_all(
				"Server", {"status": "Active", "use_for_new_benches": True}, limit=1
			)
			if servers_for_new_bench:
				self.append("servers", {"server": servers_for_new_bench[0].name})

	def create_deploy_candidate(self):
		if not self.enabled:
			return
		apps = []
		for app in self.apps:
			release = frappe.get_all(
				"App Release",
				fields=["name", "source", "app", "hash"],
				filters={"app": app.app, "source": app.source},
				order_by="creation desc",
				limit=1,
			)
			if release:
				release = release[0]
				apps.append(
					{
						"release": release.name,
						"source": release.source,
						"app": release.app,
						"hash": release.hash,
					}
				)
		frappe.get_doc(
			{"doctype": "Deploy Candidate", "group": self.name, "apps": apps}
		).insert()

	def add_app(self, source):
		self.append("apps", {"source": source.name, "app": source.app})
		self.save()


def new_release_group(title, version, apps, team=None):
	group = frappe.get_doc(
		{
			"doctype": "Release Group",
			"title": title,
			"version": version,
			"apps": apps,
			"team": team,
		}
	).insert()
	return group


def get_permission_query_conditions(user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return ""

	team = get_current_team()

	return f"(`tabRelease Group`.`team` = {frappe.db.escape(team)})"


def has_permission(doc, ptype, user):
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user
	if frappe.session.data.user_type == "System User":
		return True

	team = get_current_team()
	if doc.team == team:
		return True

	return False
