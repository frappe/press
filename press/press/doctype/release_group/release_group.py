# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from press.press.doctype.server.server import Server
import frappe

from frappe.model.document import Document
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.app_source.app_source import AppSource, create_app_source

DEFAULT_DEPENDENCIES = [
	{"dependency": "NVM_VERSION", "version": "0.36.0"},
	{"dependency": "NODE_VERSION", "version": "14.4.0"},
	{"dependency": "PYTHON_VERSION", "version": "3.7"},
	{"dependency": "WKHTMLTOPDF_VERSION", "version": "0.12.5"},
]


class ReleaseGroup(Document):
	def validate(self):
		self.validate_title()
		self.validate_frappe_app()
		self.validate_duplicate_app()
		self.validate_app_versions()
		self.validate_servers()
		self.validate_dependencies()

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
		elif self.is_new():
			server_for_new_bench = Server.get_prod_for_new_bench()
			if server_for_new_bench:
				self.append("servers", {"server": server_for_new_bench})

	@frappe.whitelist()
	def validate_dependencies(self):
		if not hasattr(self, "dependencies") or not self.dependencies:
			self.extend("dependencies", DEFAULT_DEPENDENCIES)

	@frappe.whitelist()
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
		dependencies = [
			{"dependency": d.dependency, "version": d.version} for d in self.dependencies
		]
		frappe.get_doc(
			{
				"doctype": "Deploy Candidate",
				"group": self.name,
				"apps": apps,
				"dependencies": dependencies,
			}
		).insert()

	def add_app(self, source):
		self.append("apps", {"source": source.name, "app": source.app})
		self.save()

	def change_app_branch(self, app: str, to_branch: str) -> None:
		current_app_source = self.get_app_source(app)

		# Already on that branch
		if current_app_source.branch == to_branch:
			frappe.throw(f"App already on branch {to_branch}!")

		required_app_source = frappe.get_all(
			"App Source",
			filters={"repository_url": current_app_source.repository_url, "branch": to_branch},
			limit=1,
		)

		if required_app_source:
			required_app_source = required_app_source[0]
		else:
			version = frappe.get_all(
				"App Source Version", filters={"parent": current_app_source.name}, pluck="version"
			)[0]

			required_app_source = create_app_source(
				app, current_app_source.repository_url, to_branch, version
			)

			required_app_source.github_installation_id = (
				current_app_source.github_installation_id
			)
			required_app_source.save()

		self.set_app_source(app, required_app_source.name)

	def get_app_source(self, app: str) -> AppSource:
		source = frappe.get_all(
			"Release Group App", filters={"parent": self.name, "app": app}, pluck="source"
		)

		if source:
			source = source[0]
		else:
			frappe.throw("Release group app does not exist!")

		return frappe.get_doc("App Source", source)

	def set_app_source(self, target_app: str, source: str) -> None:
		"""Set `target_app`'s source in release group to `source`"""
		for app in self.apps:
			if app.app == target_app:
				app.source = source
				app.save()
				break
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


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Release Group"
)
