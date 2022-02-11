# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
import copy

from typing import List
from frappe.core.utils import find
from frappe.model.document import Document
from press.press.doctype.server.server import Server
from press.utils import get_last_doc, get_app_tag, get_current_team, log_error
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
				frappe.throw(f"App {app.app} can be added only once", frappe.ValidationError)
			apps.add(app_name)

	def validate_app_versions(self):
		# App Source should be compatible with Release Group's version
		for app in self.apps:
			source = frappe.get_doc("App Source", app.source)
			if all(row.version != self.version for row in source.versions):
				frappe.throw(
					f"App Source {app.source} version is not {self.version}", frappe.ValidationError
				)

	def validate_servers(self):
		if self.servers:
			servers = set(server.server for server in self.servers)
			if len(servers) != len(self.servers):
				frappe.throw("Servers can be added only once", frappe.ValidationError)
		elif self.is_new():
			server_for_new_bench = Server.get_prod_for_new_bench()
			if server_for_new_bench:
				self.append("servers", {"server": server_for_new_bench})

	@frappe.whitelist()
	def validate_dependencies(self):
		# TODO: Move this to Frappe Version DocType
		dependencies = copy.deepcopy(DEFAULT_DEPENDENCIES)
		if self.version in ("Version 14", "Nightly"):
			python = find(dependencies, lambda x: x["dependency"] == "PYTHON_VERSION")
			python["version"] = "3.8"

		if self.version == "Version 12":
			node = find(dependencies, lambda x: x["dependency"] == "NODE_VERSION")
			node["version"] = "12.19.0"

		if not hasattr(self, "dependencies") or not self.dependencies:
			self.extend("dependencies", dependencies)

	@frappe.whitelist()
	def create_deploy_candidate(self, apps_to_ignore=[]):
		if not self.enabled:
			return

		# Get the deploy information for apps
		# that have updates available
		apps_deploy_info = self.deploy_information().apps

		app_updates = [
			app
			for app in apps_deploy_info
			if app["update_available"]
			and (not find(apps_to_ignore, lambda x: x["app"] == app["app"]))
		]

		apps = []
		for update in app_updates:
			apps.append(
				{
					"release": update["next_release"],
					"source": update["source"],
					"app": update["app"],
					"hash": update["next_hash"],
				}
			)

		# The apps that are in the release group
		# Not updated or ignored
		untouched_apps = [
			a for a in self.apps if not find(app_updates, lambda x: x["app"] == a.app)
		]
		last_deployed_bench = get_last_doc("Bench", {"group": self.name, "status": "Active"})

		if last_deployed_bench:
			for app in untouched_apps:
				update = find(last_deployed_bench.apps, lambda x: x.app == app.app)

				if update:
					apps.append(
						{
							"release": update.release,
							"source": update.source,
							"app": update.app,
							"hash": update.hash,
						}
					)

		dependencies = [
			{"dependency": d.dependency, "version": d.version} for d in self.dependencies
		]

		apps = self.get_sorted_based_on_rg_apps(apps)

		# Create and deploy the DC
		candidate = frappe.get_doc(
			{
				"doctype": "Deploy Candidate",
				"group": self.name,
				"apps": apps,
				"dependencies": dependencies,
			}
		).insert()

		return candidate

	def get_sorted_based_on_rg_apps(self, apps):
		# Rearrange Apps to match release group ordering
		sorted_apps = []

		for app in self.apps:
			dc_app = find(apps, lambda x: x["app"] == app.app)
			if dc_app:
				sorted_apps.append(dc_app)

		for app in apps:
			if not find(sorted_apps, lambda x: x["app"] == app["app"]):
				sorted_apps.append(app)

		return sorted_apps

	@frappe.whitelist()
	def deploy_information(self):
		out = frappe._dict(update_available=False)

		last_deployed_bench = get_last_doc("Bench", {"group": self.name, "status": "Active"})
		out.apps = self.get_app_updates(
			last_deployed_bench.apps if last_deployed_bench else []
		)
		out.removed_apps = self.get_removed_apps()
		out.update_available = any([app["update_available"] for app in out.apps]) or (
			len(out.removed_apps) > 0
		)

		return out

	def get_app_updates(self, current_apps):
		next_apps = self.get_next_apps(current_apps)

		apps = []
		for app in next_apps:
			bench_app = find(current_apps, lambda x: x.app == app.app)
			current_hash = bench_app.hash if bench_app else None
			source = frappe.get_doc("App Source", app.source)

			will_branch_change = False
			current_branch = source.branch
			if bench_app:
				current_source = frappe.get_doc("App Source", bench_app.source)
				will_branch_change = current_source.branch != source.branch
				current_branch = current_source.branch

			current_tag = (
				get_app_tag(source.repository, source.repository_owner, current_hash)
				if current_hash
				else None
			)
			next_hash = app.hash
			apps.append(
				{
					"title": app.title,
					"app": app.app,
					"source": source.name,
					"repository": source.repository,
					"repository_owner": source.repository_owner,
					"repository_url": source.repository_url,
					"branch": source.branch,
					"current_hash": current_hash,
					"current_tag": current_tag,
					"current_release": bench_app.release if bench_app else None,
					"next_release": app.release,
					"next_hash": next_hash,
					"next_tag": get_app_tag(source.repository, source.repository_owner, next_hash),
					"will_branch_change": will_branch_change,
					"current_branch": current_branch,
					"update_available": not current_hash or current_hash != next_hash,
				}
			)
		return apps

	def get_next_apps(self, current_apps):
		marketplace_app_sources = self.get_marketplace_app_sources()
		current_team = get_current_team()
		only_approved_for_sources = [
			source
			for source in marketplace_app_sources
			if frappe.db.get_value("App Source", source, "team") != current_team
		]

		next_apps = []
		for app in self.apps:
			# TODO: Optimize using get_value, maybe?
			latest_app_release = None

			if app.source in only_approved_for_sources:
				latest_app_release = get_last_doc(
					"App Release", {"source": app.source, "status": "Approved"}
				)
			else:
				latest_app_release = get_last_doc("App Release", {"source": app.source})

			# No release exists for this source
			if not latest_app_release:
				continue

			bench_app = find(current_apps, lambda x: x.app == app.app)

			upcoming_release = (
				latest_app_release.name if latest_app_release else bench_app.release
			)
			upcoming_hash = latest_app_release.hash if latest_app_release else bench_app.hash

			next_apps.append(
				frappe._dict(
					{
						"app": app.app,
						"source": app.source,
						"release": upcoming_release,
						"hash": upcoming_hash,
						"title": app.title,
					}
				)
			)

		return next_apps

	def get_removed_apps(self):
		# Apps that were removed from the release group
		# but were in the last deployed bench
		removed_apps = []

		latest_bench = get_last_doc("Bench", {"group": self.name, "status": "Active"})

		if latest_bench:
			bench_apps = latest_bench.apps

			for bench_app in bench_apps:
				if not find(self.apps, lambda rg_app: rg_app.app == bench_app.app):
					app_title = frappe.db.get_value("App", bench_app.app, "title")
					removed_apps.append({"name": bench_app.app, "title": app_title})

		return removed_apps

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
			versions = frappe.get_all(
				"App Source Version", filters={"parent": current_app_source.name}, pluck="version"
			)

			required_app_source = create_app_source(
				app, current_app_source.repository_url, to_branch, versions
			)
			required_app_source.reload()
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

	def get_marketplace_app_sources(self) -> List[str]:
		all_marketplace_sources = frappe.get_all("Marketplace App Version", pluck="source")
		marketplace_app_sources = [
			app.source for app in self.apps if app.source in all_marketplace_sources
		]

		return marketplace_app_sources

	def get_clusters(self):
		"""Get unique clusters corresponding to self.servers"""
		servers = frappe.db.get_all(
			"Release Group Server", {"parent": self.name}, pluck="server"
		)
		return frappe.get_all(
			"Server", {"name": ("in", servers)}, pluck="cluster", distinct=True
		)

	def add_cluster(self, cluster: str):
		"""
		Add new server belonging to cluster.

		Deploys bench if no update available
		"""
		server = Server.get_prod_for_new_bench({"cluster": cluster})
		if not server:
			log_error("No suitable server for new bench")
			frappe.throw(f"No suitable server for new bench in {cluster}")
		app_update_available = self.deploy_information().update_available
		self.add_server(server, deploy=not app_update_available)

	def add_server(self, server: str, deploy=False):
		self.append("servers", {"server": server, "default": False})
		self.save()
		if deploy:
			last_successful_candidate = frappe.get_last_doc(
				"Deploy Candidate", {"status": "Success", "group": self.name}
			)
			last_successful_candidate._create_deploy([server], staging=False)


def new_release_group(title, version, apps, team=None, cluster=None):
	if cluster:
		server = frappe.get_all(
			"Server",
			{"status": "Active", "cluster": cluster, "use_for_new_benches": True},
			pluck="name",
			limit=1,
		)[0]
		servers = [{"server": server}]
	else:
		servers = []
	group = frappe.get_doc(
		{
			"doctype": "Release Group",
			"title": title,
			"version": version,
			"apps": apps,
			"servers": servers,
			"team": team,
		}
	).insert()
	return group


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Release Group"
)
