# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from contextlib import suppress
from functools import cached_property
from itertools import chain
import frappe
from frappe.utils import comma_and, flt
import json
from typing import List
from frappe.core.doctype.version.version import get_diff
from frappe.core.utils import find, find_all
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from press.press.doctype.server.server import Server
from press.utils import (
	get_last_doc,
	get_app_tag,
	get_current_team,
	log_error,
	get_client_blacklisted_keys,
)
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.app_source.app_source import AppSource, create_app_source
from typing import TYPE_CHECKING
from frappe.utils import cstr
from frappe import _
import semantic_version as sv

if TYPE_CHECKING:
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.release_group_app.release_group_app import ReleaseGroupApp

DEFAULT_DEPENDENCIES = [
	{"dependency": "NVM_VERSION", "version": "0.36.0"},
	{"dependency": "NODE_VERSION", "version": "14.19.0"},
	{"dependency": "PYTHON_VERSION", "version": "3.7"},
	{"dependency": "WKHTMLTOPDF_VERSION", "version": "0.12.5"},
	{"dependency": "BENCH_VERSION", "version": "5.15.2"},
]


class ReleaseGroup(Document):
	whitelisted_fields = ["title", "version"]

	@staticmethod
	def get_list_query(query):
		ReleaseGroup = frappe.qb.DocType("Release Group")
		Bench = frappe.qb.DocType("Bench")
		Site = frappe.qb.DocType("Site")

		site_count = (
			frappe.qb.from_(Site)
			.select(frappe.query_builder.functions.Count("*"))
			.where(Site.group == ReleaseGroup.name)
			.where(Site.status != "Archived")
		)

		active_benches = (
			frappe.qb.from_(Bench)
			.select(frappe.query_builder.functions.Count("*"))
			.where(Bench.group == ReleaseGroup.name)
			.where(Bench.status == "Active")
		)

		query = (
			query.where(ReleaseGroup.team == frappe.local.team().name)
			.where(ReleaseGroup.enabled == 1)
			.where(ReleaseGroup.public == 0)
			.select(site_count.as_("site_count"), active_benches.as_("active_benches"))
		)

		return query

	def get_doc(self, doc):
		doc.deploy_information = self.deploy_information()
		doc.status = self.status

	def validate(self):
		self.validate_title()
		self.validate_frappe_app()
		self.validate_duplicate_app()
		self.validate_app_versions()
		self.validate_servers()
		self.validate_rq_queues()
		self.validate_max_min_workers()
		self.validate_feature_flags()

	def before_insert(self):
		# to avoid ading deps while cloning a release group
		if len(self.dependencies) == 0:
			self.fetch_dependencies()

	def on_update(self):
		old_doc = self.get_doc_before_save()
		if self.flags.in_insert or self.is_new() or not old_doc:
			return
		diff = get_diff(old_doc, self) or {}
		for row in chain(diff.get("row_changed", []), diff.get("added", [])):
			if row[0] == "dependencies":
				self.db_set("last_dependency_update", frappe.utils.now_datetime())
				break

	def on_trash(self):
		candidates = frappe.get_all("Deploy Candidate", {"group": self.name})
		for candidate in candidates:
			frappe.delete_doc("Deploy Candidate", candidate.name)

	def before_save(self):
		self.update_common_site_config_preview()

	def update_common_site_config_preview(self):
		"""Regenerates rg.common_site_config on each rg.befor_save
		from the rg.common_site_config child table data"""
		new_config = {}

		for row in self.common_site_config_table:
			# update internal flag from master
			row.internal = frappe.db.get_value("Site Config Key", row.key, "internal")
			key_type = row.type or row.get_type()
			if key_type == "Password":
				# we don't support password type yet!
				key_type = "String"
			row.type = key_type

			if key_type == "Number":
				key_value = (
					int(row.value) if isinstance(row.value, (float, int)) else json.loads(row.value)
				)
			elif key_type == "Boolean":
				key_value = (
					row.value if isinstance(row.value, bool) else bool(json.loads(cstr(row.value)))
				)
			elif key_type == "JSON":
				key_value = json.loads(cstr(row.value))
			else:
				key_value = row.value

			new_config[row.key] = key_value

		self.common_site_config = json.dumps(new_config, indent=4)

	@frappe.whitelist()
	def update_dependency(self, dependency_name, version):
		"""Updates a dependency version in the Release Group Dependency table"""

		for dependency in self.dependencies:
			if dependency.name == dependency_name:
				dependency.version = version
				self.save()
				return

	@frappe.whitelist()
	def delete_config(self, key):
		"""Deletes a key from the common_site_config_table"""

		if key in get_client_blacklisted_keys():
			return

		updated_common_site_config = []
		for row in self.common_site_config_table:
			if row.key != key and not row.internal:
				updated_common_site_config.append(
					{"key": row.key, "value": row.value, "type": row.type}
				)

		# using a tuple to avoid updating bench_config
		# TODO: remove tuple when bench_config is removed and field for http_timeout is added
		self.update_config_in_release_group(updated_common_site_config, ())

	@frappe.whitelist()
	def update_config(self, config):
		sanitized_common_site_config = [
			{"key": c.key, "type": c.type, "value": c.value}
			for c in self.common_site_config_table
		]

		config = frappe.parse_json(config)

		for key, value in config.items():
			if key in get_client_blacklisted_keys():
				continue

			if isinstance(value, (dict, list)):
				_type = "JSON"
			elif isinstance(value, bool):
				_type = "Boolean"
			elif isinstance(value, (int, float)):
				_type = "Number"
			else:
				_type = "String"

			if frappe.db.exists("Site Config Key", key):
				_type = frappe.db.get_value("Site Config Key", key, "type")

			if _type == "Number":
				value = flt(value)
			elif _type == "Boolean":
				value = bool(value)
			elif _type == "JSON":
				value = frappe.parse_json(value)

			# update existing key
			for row in sanitized_common_site_config:
				if row["key"] == key:
					row["value"] = value
					row["type"] = _type
					break
			else:
				sanitized_common_site_config.append({"key": key, "value": value, "type": _type})

		# using a tuple to avoid updating bench_config
		# TODO: remove tuple when bench_config is removed and field for http_timeout is added
		self.update_config_in_release_group(sanitized_common_site_config, ())

	def update_config_in_release_group(self, common_site_config, bench_config):
		"""Updates bench_config and common_site_config in the Release Group

		Args:
		config (list): List of dicts with key, value, and type
		"""
		blacklisted_config = [
			x for x in self.common_site_config_table if x.key in get_client_blacklisted_keys()
		]
		self.common_site_config_table = []

		# Maintain keys that aren't accessible to Dashboard user
		for i, _config in enumerate(blacklisted_config):
			_config.idx = i + 1
			self.common_site_config_table.append(_config)

		for d in common_site_config:
			d = frappe._dict(d)
			if isinstance(d.value, (dict, list)):
				value = json.dumps(d.value)
			else:
				value = d.value
			self.append(
				"common_site_config_table", {"key": d.key, "value": value, "type": d.type}
			)

		for d in bench_config:
			if d.key == "http_timeout":
				# http_timeout should be the only thing configurable in bench_config
				self.bench_config = json.dumps({"http_timeout": int(d.value)}, indent=4)
		if bench_config == []:
			self.bench_config = json.dumps({})

		self.save()

	def validate_title(self):
		if frappe.get_all(
			"Release Group",
			{
				"title": self.title,
				"team": self.team or "",
				"name": ("!=", self.name),
				"enabled": True,
			},
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
		with suppress(AttributeError):
			if (
				not frappe.flags.in_test
				and frappe.request.path == "/api/method/press.api.bench.change_branch"
			):
				return  # Separate validation exists in set_app_source
		for app in self.apps:
			self.validate_app_version(app)

	def validate_app_version(self, app: "ReleaseGroupApp"):
		source = frappe.get_doc("App Source", app.source)
		if all(row.version != self.version for row in source.versions):
			branch, repo = frappe.db.get_values(
				"App Source", app.source, ("branch", "repository")
			)[0]
			msg = f"{repo.rsplit('/')[-1] or repo.rsplit('/')[-2]}:{branch} branch is no longer compatible with {self.version} version of Frappe"
			frappe.throw(msg, frappe.ValidationError)

	def validate_servers(self):
		if self.servers:
			servers = set(server.server for server in self.servers)
			if len(servers) != len(self.servers):
				frappe.throw("Servers can be added only once", frappe.ValidationError)
		elif self.is_new():
			server_for_new_bench = Server.get_prod_for_new_bench()
			if server_for_new_bench:
				self.append("servers", {"server": server_for_new_bench})

	def fetch_dependencies(self):
		frappe_version = frappe.get_doc("Frappe Version", self.version)

		for d in frappe_version.dependencies:
			self.append("dependencies", {"dependency": d.dependency, "version": d.version})

	def validate_rq_queues(self):
		if self.merge_all_rq_queues and self.merge_default_and_short_rq_queues:
			frappe.throw(
				"Can't set Merge All RQ Queues and Merge Short and Default RQ Queues at once",
				frappe.ValidationError,
			)

	def validate_max_min_workers(self):
		if self.max_gunicorn_workers and self.min_gunicorn_workers:
			if self.max_gunicorn_workers < self.min_gunicorn_workers:
				frappe.throw(
					"Max Gunicorn Workers can't be less than Min Gunicorn Workers",
					frappe.ValidationError,
				)
		if self.max_background_workers and self.min_background_workers:
			if self.max_background_workers < self.min_background_workers:
				frappe.throw(
					"Max Background Workers can't be less than Min Background Workers",
					frappe.ValidationError,
				)

	def validate_feature_flags(self) -> None:
		if self.use_app_cache and not self.can_use_get_app_cache():
			frappe.throw(_("Use App Cache cannot be set, BENCH_VERSION must be 5.21.2 or later"))

	def can_use_get_app_cache(self) -> bool:
		version = find(
			self.dependencies,
			lambda x: x.dependency == "BENCH_VERSION",
		).version

		try:
			return sv.Version(version) in sv.SimpleSpec(">=5.21.3")
		except ValueError:
			return False

	@frappe.whitelist()
	def create_duplicate_deploy_candidate(self):
		return self.create_deploy_candidate([])

	@frappe.whitelist()
	def create_deploy_candidate(self, apps_to_update=None) -> "DeployCandidate":
		if not self.enabled:
			return

		apps = self.get_apps_to_update(apps_to_update)

		dependencies = [
			{"dependency": d.dependency, "version": d.version} for d in self.dependencies
		]

		packages = [
			{
				"package_manager": p.package_manager,
				"package": p.package,
				"package_prerequisites": p.package_prerequisites,
				"after_install": p.after_install,
			}
			for p in self.packages
		]

		environment_variables = [
			{"key": v.key, "value": v.value} for v in self.environment_variables
		]

		# Create and deploy the DC
		candidate = frappe.get_doc(
			{
				"doctype": "Deploy Candidate",
				"group": self.name,
				"apps": apps,
				"dependencies": dependencies,
				"packages": packages,
				"environment_variables": environment_variables,
			}
		).insert()

		return candidate

	def get_apps_to_update(self, apps_to_update):
		# If apps_to_update is None, try to update all apps
		if apps_to_update is None:
			apps_to_update = self.apps

		apps = []
		last_deployed_bench = get_last_doc("Bench", {"group": self.name, "status": "Active"})

		for app in self.deploy_information().apps:
			app_to_update = find(apps_to_update, lambda x: x.get("app") == app.app)
			# If we want to update the app and there's an update available
			if app_to_update and app["update_available"]:
				# Use a specific release if mentioned, otherwise pick the most recent one
				target_release = app_to_update.get("release", app.next_release)
				apps.append(
					{
						"app": app["app"],
						"source": app["source"],
						"release": target_release,
						"hash": frappe.db.get_value("App Release", target_release, "hash"),
					}
				)
			else:
				# Either we don't want to update the app or there's no update available
				if last_deployed_bench:
					# Find the last deployed release and use it
					app_to_keep = find(last_deployed_bench.apps, lambda x: x.app == app.app)
					if app_to_keep:
						apps.append(
							{
								"app": app_to_keep.app,
								"source": app_to_keep.source,
								"release": app_to_keep.release,
								"hash": app_to_keep.hash,
							}
						)

		return self.get_sorted_based_on_rg_apps(apps)

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
		out.last_deploy = self.last_dc_info
		out.deploy_in_progress = self.deploy_in_progress

		out.removed_apps = self.get_removed_apps()
		out.update_available = (
			any([app["update_available"] for app in out.apps])
			or (len(out.removed_apps) > 0)
			or self.dependency_update_pending
		)
		out.number_of_apps = len(self.apps)

		out.sites = [
			site.update({"skip_failing_patches": False, "skip_backups": False})
			for site in frappe.get_all(
				"Site", {"group": self.name, "status": "Active"}, ["name", "server", "bench"]
			)
		]

		return out

	@frappe.whitelist()
	def deployed_versions(self):
		Bench = frappe.qb.DocType("Bench")
		Server = frappe.qb.DocType("Server")
		deployed_versions = (
			frappe.qb.from_(Bench)
			.left_join(Server)
			.on(Server.name == Bench.server)
			.where((Bench.group == self.name) & (Bench.status != "Archived"))
			.groupby(Bench.name)
			.select(Bench.name, Bench.status, Bench.is_ssh_proxy_setup, Server.proxy_server)
			.orderby(Bench.creation, order=frappe.qb.desc)
			.run(as_dict=True)
		)

		rg_version = self.version

		sites_in_group_details = frappe.db.get_all(
			"Site",
			filters={
				"group": self.name,
				"status": ("not in", ("Archived", "Suspended")),
				"is_standby": 0,
			},
			fields=["name", "status", "cluster", "plan", "creation", "bench"],
		)

		Cluster = frappe.qb.DocType("Cluster")
		cluster_data = (
			frappe.qb.from_(Cluster)
			.select(Cluster.name, Cluster.title, Cluster.image)
			.where((Cluster.name.isin([site.cluster for site in sites_in_group_details])))
			.run(as_dict=True)
		)

		Plan = frappe.qb.DocType("Plan")
		plan_data = (
			frappe.qb.from_(Plan)
			.select(Plan.name, Plan.plan_title, Plan.price_inr, Plan.price_usd)
			.where((Plan.name.isin([site.plan for site in sites_in_group_details])))
			.run(as_dict=True)
		)

		ResourceTag = frappe.qb.DocType("Resource Tag")
		tag_data = (
			frappe.qb.from_(ResourceTag)
			.select(ResourceTag.tag_name, ResourceTag.parent)
			.where((ResourceTag.parent.isin([site.name for site in sites_in_group_details])))
			.run(as_dict=True)
		)

		cur_user_ssh_key = frappe.get_all(
			"User SSH Key", {"user": frappe.session.user, "is_default": 1}, limit=1
		)
		for version in deployed_versions:
			version.has_ssh_access = version.is_ssh_proxy_setup and cur_user_ssh_key
			version.sites = find_all(sites_in_group_details, lambda x: x.bench == version.name)
			for site in version.sites:
				site.version = rg_version
				site.server_region_info = find(cluster_data, lambda x: x.name == site.cluster)
				site.plan = find(plan_data, lambda x: x.name == site.plan)
				tags = find_all(tag_data, lambda x: x.parent == site.name)
				site.tags = [tag.tag_name for tag in tags]

			version.deployed_on = frappe.db.get_value(
				"Agent Job",
				{"bench": version.name, "job_type": "New Bench", "status": "Success"},
				"end",
			)

		return deployed_versions

	@frappe.whitelist()
	def get_app_versions(self, bench):
		apps = frappe.db.get_all(
			"Bench App",
			{"parent": bench},
			["name", "app", "hash", "source"],
			order_by="idx",
		)
		for app in apps:
			app.update(
				frappe.db.get_value(
					"App Source",
					app.source,
					("branch", "repository", "repository_owner", "repository_url"),
					as_dict=1,
					cache=True,
				)
			)
			app.tag = get_app_tag(app.repository, app.repository_owner, app.hash)
		return apps

	@frappe.whitelist()
	def generate_certificate(self):
		user_ssh_key = frappe.get_all(
			"User SSH Key", {"user": frappe.session.user, "is_default": True}, pluck="name"
		)[0]
		return frappe.get_doc(
			{
				"doctype": "SSH Certificate",
				"certificate_type": "User",
				"group": self.name,
				"user": frappe.session.user,
				"user_ssh_key": user_ssh_key,
				"validity": "6h",
			}
		).insert()

	@frappe.whitelist()
	def get_certificate(self):
		certificates = frappe.get_all(
			"SSH Certificate",
			{
				"user": frappe.session.user,
				"valid_until": [">", frappe.utils.now()],
				"group": self.name,
			},
			pluck="name",
			limit=1,
		)
		if certificates:
			return frappe.get_doc("SSH Certificate", certificates[0])
		return False

	@property
	def dependency_update_pending(self):
		if not self.last_dependency_update or not self.last_dc_info:
			return False
		return (
			frappe.utils.get_datetime(self.last_dependency_update) > self.last_dc_info.creation
		)

	@property
	def deploy_in_progress(self):
		return self.last_dc_info and self.last_dc_info.status in ("Running", "Scheduled")

	@property
	def status(self):
		active_benches = frappe.db.get_all(
			"Bench", {"group": self.name, "status": "Active"}, limit=1, order_by="creation desc"
		)
		return "Active" if active_benches else "Awaiting Deploy"

	@cached_property
	def last_dc_info(self):
		dc = frappe.qb.DocType("Deploy Candidate")

		query = (
			frappe.qb.from_(dc)
			.where(dc.group == self.name)
			.select(dc.name, dc.status, dc.creation)
			.orderby(dc.creation, order=frappe.qb.desc)
			.limit(1)
		)

		results = query.run(as_dict=True)

		if len(results) > 0:
			return results[0]

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
				current_source_branch = frappe.db.get_value(
					"App Source", bench_app.source, "branch"
				)
				will_branch_change = current_source_branch != source.branch
				current_branch = current_source_branch

			current_tag = (
				get_app_tag(source.repository, source.repository_owner, current_hash)
				if current_hash
				else None
			)

			for release in app.releases:
				release.tag = get_app_tag(source.repository, source.repository_owner, release.hash)

			next_hash = app.hash

			update_available = not current_hash or current_hash != next_hash
			if not app.releases:
				update_available = False

			apps.append(
				frappe._dict(
					{
						"title": app.title,
						"app": app.app,  # remove this line once dashboard1 is removed
						"name": app.app,
						"source": source.name,
						"repository": source.repository,
						"repository_owner": source.repository_owner,
						"repository_url": source.repository_url,
						"branch": source.branch,
						"current_hash": current_hash,
						"current_tag": current_tag,
						"current_release": bench_app.release if bench_app else None,
						"releases": app.releases,
						"next_release": app.release,
						"will_branch_change": will_branch_change,
						"current_branch": current_branch,
						"update_available": update_available,
					}
				)
			)
		return apps

	def get_next_apps(self, current_apps):
		marketplace_app_sources = self.get_marketplace_app_sources()
		current_team = get_current_team(True)
		app_publishers_team = [current_team.name]

		if current_team.parent_team:
			app_publishers_team.append(current_team.parent_team)

		only_approved_for_sources = [self.apps[0].source]  # add frappe app source
		if marketplace_app_sources:
			AppSource = frappe.qb.DocType("App Source")
			only_approved_for_sources.append(
				frappe.qb.from_(AppSource)
				.where(AppSource.name.isin(marketplace_app_sources))
				.where(AppSource.team.notin(app_publishers_team))
				.select(AppSource.name)
				.run(as_dict=True, pluck="name")
			)

		next_apps = []

		app_sources = [app.source for app in self.apps]
		AppRelease = frappe.qb.DocType("App Release")
		latest_releases = (
			frappe.qb.from_(AppRelease)
			.where(AppRelease.source.isin(app_sources))
			.select(
				AppRelease.name,
				AppRelease.source,
				AppRelease.status,
				AppRelease.hash,
				AppRelease.message,
				AppRelease.creation,
			)
			.orderby(AppRelease.creation, order=frappe.qb.desc)
			.run(as_dict=True)
		)

		for app in self.apps:
			latest_app_release = None
			latest_app_releases = find_all(latest_releases, lambda x: x.source == app.source)

			if app.source in only_approved_for_sources:
				latest_app_release = find(latest_app_releases, lambda x: x.status == "Approved")
				latest_app_releases = find_all(
					latest_app_releases, lambda x: x.status == "Approved"
				)
			else:
				latest_app_release = find(latest_app_releases, lambda x: x.source == app.source)

			# No release exists for this source
			if not latest_app_release:
				continue

			bench_app = find(current_apps, lambda x: x.app == app.app)

			upcoming_release = (
				latest_app_release.name if latest_app_release else bench_app.release
			)
			upcoming_hash = latest_app_release.hash if latest_app_release else bench_app.hash

			upcoming_releases = latest_app_releases
			if bench_app:
				new_branch = frappe.db.get_value("App Source", app.source, "branch")
				old_branch = frappe.db.get_value("App Source", bench_app.source, "branch")

				if new_branch == old_branch:
					current_release_creation = frappe.db.get_value(
						"App Release", bench_app.release, "creation"
					)
					upcoming_releases = [
						release
						for release in latest_app_releases
						if release.creation > current_release_creation
					]

			next_apps.append(
				frappe._dict(
					{
						"app": app.app,
						"source": app.source,
						"release": upcoming_release,
						"hash": upcoming_hash,
						"title": app.title,
						"releases": upcoming_releases[:16],
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

	@frappe.whitelist()
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
		self.validate_app_version(app)
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

	@frappe.whitelist()
	def add_region(self, region):
		"""
		Add new region to release group (limits to 2). Meant for dashboard use only.
		"""

		if len(self.get_clusters()) >= 2:
			frappe.throw("More than 2 regions for bench not allowed")
		self.add_cluster(region)

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

	def get_last_successful_candidate(self) -> Document:
		return frappe.get_last_doc(
			"Deploy Candidate", {"status": "Success", "group": self.name}
		)

	@frappe.whitelist()
	def add_server(self, server: str, deploy=False):
		self.append("servers", {"server": server, "default": False})
		self.save()
		if deploy:
			return self.get_last_successful_candidate()._create_deploy([server], staging=False)

	@frappe.whitelist()
	def change_server(self, server: str):
		"""
		Create latest candidate in given server and tries to move sites there.

		If only 1 server in server list, removes it, else schedules site
		migrations from first server in list to given.
		"""
		if len(self.servers) == 1:
			self.remove(self.servers[0])
		self.add_server(server, deploy=True)

	@frappe.whitelist()
	def update_benches_config(self):
		"""Update benches config for all benches in the release group"""
		benches = frappe.get_all("Bench", "name", {"group": self.name, "status": "Active"})
		for bench in benches:
			frappe.get_doc("Bench", bench.name).update_bench_config(force=True)

	@frappe.whitelist()
	def remove_app(self, app: str):
		"""Remove app from release group"""

		sites = frappe.get_all(
			"Site", filters={"group": self.name, "status": ("!=", "Archived")}, pluck="name"
		)

		site_apps = frappe.get_all(
			"Site App", filters={"parent": ("in", sites), "app": app}, fields=["parent"]
		)

		if site_apps:
			installed_on_sites = ", ".join(
				frappe.bold(site_app["parent"]) for site_app in site_apps
			)
			frappe.throw(
				"Cannot remove this app, it is already installed on the"
				f" site(s): {comma_and(installed_on_sites, add_quotes=False)}"
			)

		app_doc_to_remove = find(self.apps, lambda x: x.app == app)
		if app_doc_to_remove:
			self.remove(app_doc_to_remove)

		self.save()
		return app

	@frappe.whitelist()
	def fetch_latest_app_update(self, app: str):
		app_source = self.get_app_source(app)
		app_source.create_release(force=True)

	@frappe.whitelist()
	def archive(self):
		benches = frappe.get_all(
			"Bench", filters={"group": self.name, "status": "Active"}, pluck="name"
		)
		for bench in benches:
			frappe.get_doc("Bench", bench).archive()

		new_name = f"{self.title}.archived"
		self.title = append_number_if_name_exists(
			"Release Group", new_name, "title", separator="."
		)
		self.enabled = 0
		self.save()


def new_release_group(
	title, version, apps, team=None, cluster=None, saas_app="", server=None
):
	if cluster:
		if not server:
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
			"saas_app": saas_app,
		}
	).insert()
	return group


def get_status(name):
	return (
		"Active"
		if frappe.get_all(
			"Bench", {"group": name, "status": "Active"}, limit=1, order_by="creation desc"
		)
		else "Awaiting Deploy"
	)


get_permission_query_conditions = get_permission_query_conditions_for_doctype(
	"Release Group"
)
