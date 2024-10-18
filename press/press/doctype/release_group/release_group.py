# For license information, please see license.txt
from __future__ import annotations

import json
from contextlib import suppress
from functools import cached_property
from itertools import chain
from typing import TYPE_CHECKING, TypedDict

import frappe
import frappe.query_builder
import semantic_version as sv
from frappe import _
from frappe.core.doctype.version.version import get_diff
from frappe.core.utils import find, find_all
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists
from frappe.query_builder.functions import Count
from frappe.utils import cstr, flt, get_url, sbool
from frappe.utils.caching import redis_cache

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.press.doctype.app.app import new_app
from press.press.doctype.app_source.app_source import AppSource, create_app_source
from press.press.doctype.deploy_candidate.utils import is_suspended
from press.press.doctype.resource_tag.tag_helpers import TagHelpers
from press.press.doctype.server.server import Server
from press.utils import (
	get_app_tag,
	get_client_blacklisted_keys,
	get_current_team,
	get_last_doc,
	log_error,
)

if TYPE_CHECKING:
	from datetime import datetime
	from typing import Any

DEFAULT_DEPENDENCIES = [
	{"dependency": "NVM_VERSION", "version": "0.36.0"},
	{"dependency": "NODE_VERSION", "version": "14.19.0"},
	{"dependency": "PYTHON_VERSION", "version": "3.7"},
	{"dependency": "WKHTMLTOPDF_VERSION", "version": "0.12.5"},
	{"dependency": "BENCH_VERSION", "version": "5.15.2"},
]


class LastDeployInfo(TypedDict):
	name: str
	status: str
	creation: datetime


if TYPE_CHECKING:
	from press.press.doctype.app.app import App
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


class ReleaseGroup(Document, TagHelpers):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.common_site_config.common_site_config import CommonSiteConfig
		from press.press.doctype.release_group_app.release_group_app import ReleaseGroupApp
		from press.press.doctype.release_group_dependency.release_group_dependency import (
			ReleaseGroupDependency,
		)
		from press.press.doctype.release_group_mount.release_group_mount import (
			ReleaseGroupMount,
		)
		from press.press.doctype.release_group_package.release_group_package import (
			ReleaseGroupPackage,
		)
		from press.press.doctype.release_group_server.release_group_server import (
			ReleaseGroupServer,
		)
		from press.press.doctype.release_group_variable.release_group_variable import (
			ReleaseGroupVariable,
		)
		from press.press.doctype.resource_tag.resource_tag import ResourceTag

		apps: DF.Table[ReleaseGroupApp]
		bench_config: DF.Code | None
		build_server: DF.Link | None
		central_bench: DF.Check
		common_site_config: DF.Code | None
		common_site_config_table: DF.Table[CommonSiteConfig]
		compress_app_cache: DF.Check
		default: DF.Check
		dependencies: DF.Table[ReleaseGroupDependency]
		enabled: DF.Check
		environment_variables: DF.Table[ReleaseGroupVariable]
		gunicorn_threads_per_worker: DF.Int
		is_code_server_enabled: DF.Check
		is_push_to_deploy_enabled: DF.Check
		is_redisearch_enabled: DF.Check
		last_dependency_update: DF.Datetime | None
		max_background_workers: DF.Int
		max_gunicorn_workers: DF.Int
		merge_all_rq_queues: DF.Check
		merge_default_and_short_rq_queues: DF.Check
		min_background_workers: DF.Int
		min_gunicorn_workers: DF.Int
		mounts: DF.Table[ReleaseGroupMount]
		packages: DF.Table[ReleaseGroupPackage]
		public: DF.Check
		saas_app: DF.Link | None
		saas_bench: DF.Check
		servers: DF.Table[ReleaseGroupServer]
		tags: DF.Table[ResourceTag]
		team: DF.Link
		title: DF.Data
		use_app_cache: DF.Check
		use_delta_builds: DF.Check
		use_rq_workerpool: DF.Check
		version: DF.Link
	# end: auto-generated types

	dashboard_fields = ("title", "version", "apps", "team", "public", "tags")

	@staticmethod
	def get_list_query(query, filters, **list_args):
		ReleaseGroupServer = frappe.qb.DocType("Release Group Server")
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

		if server := filters.get("server"):
			query = (
				query.inner_join(ReleaseGroupServer)
				.on(ReleaseGroupServer.parent == ReleaseGroup.name)
				.where(ReleaseGroupServer.server == server)
			)

		return query

	def get_doc(self, doc):
		doc.deploy_information = self.deploy_information()
		doc.status = self.status
		doc.actions = self.get_actions()
		doc.are_builds_suspended = are_builds_suspended()

		if len(self.servers) == 1:
			server = frappe.db.get_value("Server", self.servers[0].server, ["team", "title"], as_dict=True)
			doc.server = self.servers[0].server
			doc.server_title = server.title
			doc.server_team = server.team

		doc.enable_inplace_updates = frappe.get_value(
			"Team",
			self.team,
			"enable_inplace_updates",
		)
		if doc.enable_inplace_updates:
			doc.inplace_update_failed_benches = self.get_inplace_update_failed_benches()

	def get_inplace_update_failed_benches(self):
		return frappe.db.get_all(
			"Bench",
			{"group": self.name, "status": "Active", "last_inplace_update_failed": True},
			pluck="name",
		)

	def get_actions(self):
		return [
			{
				"action": "Rename Bench Group",
				"description": "Rename the bench group",
				"button_label": "Rename",
				"doc_method": "rename",
			},
			{
				"action": "Transfer Bench Group",
				"description": "Transfer ownership of this bench group to another team",
				"button_label": "Transfer",
				"doc_method": "send_change_team_request",
			},
			{
				"action": "Drop Bench Group",
				"description": "Drop the bench group",
				"button_label": "Drop",
				"doc_method": "drop",
				"group": "Dangerous Actions",
			},
		]

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
		self.set_default_app_cache_flags()
		self.set_default_delta_builds_flags()

	def after_insert(self):
		from press.press.doctype.press_role.press_role import (
			add_permission_for_newly_created_doc,
		)

		add_permission_for_newly_created_doc(self)

	def on_update(self):
		old_doc = self.get_doc_before_save()
		if self.flags.in_insert or self.is_new() or not old_doc:
			return
		diff = get_diff(old_doc, self) or {}
		for row in chain(diff.get("row_changed", []), diff.get("added", [])):
			if row[0] == "dependencies":
				self.db_set("last_dependency_update", frappe.utils.now_datetime())
				break
		if self.has_value_changed("team"):
			frappe.db.delete("Press Role Permission", {"release_group": self.name})

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
			row.type = key_type

			if key_type == "Number":
				key_value = int(row.value) if isinstance(row.value, (float, int)) else json.loads(row.value)
			elif key_type == "Boolean":
				key_value = row.value if isinstance(row.value, bool) else bool(json.loads(cstr(row.value)))
			elif key_type == "JSON":
				key_value = json.loads(cstr(row.value))
			else:
				key_value = row.value

			new_config[row.key] = key_value

		self.common_site_config = json.dumps(new_config, indent=4)

	@dashboard_whitelist()
	def update_dependency(self, dependency_name, version, is_custom):
		"""Updates a dependency version in the Release Group Dependency table"""
		for dependency in self.dependencies:
			if dependency.name == dependency_name:
				dependency.version = version
				dependency.is_custom = is_custom
				self.save()
				return

	@dashboard_whitelist()
	def delete_config(self, key):
		"""Deletes a key from the common_site_config_table"""

		if key in get_client_blacklisted_keys():
			return

		updated_common_site_config = []
		for row in self.common_site_config_table:
			if row.key != key and not row.internal:
				updated_common_site_config.append({"key": row.key, "value": row.value, "type": row.type})

		# using a tuple to avoid updating bench_config
		# TODO: remove tuple when bench_config is removed and field for http_timeout is added
		self.update_config_in_release_group(updated_common_site_config, ())

	@dashboard_whitelist()
	def update_config(self, config):
		sanitized_common_site_config = [
			{"key": c.key, "type": c.type, "value": c.value} for c in self.common_site_config_table
		]

		config = frappe.parse_json(config)

		for key, value in config.items():
			if key in get_client_blacklisted_keys():
				frappe.throw(_(f"The key <b>{key}</b> is blacklisted or is internal and cannot be updated"))

			config_type = get_config_type(value)

			if frappe.db.exists("Site Config Key", key):
				config_type = frappe.db.get_value("Site Config Key", key, "type")

			value = get_formatted_config_value(
				config_type,
				value,
				key,
				self.name,
			)

			# update existing key
			for row in sanitized_common_site_config:
				if row["key"] == key:
					row["value"] = value
					row["type"] = config_type
					break
			else:
				sanitized_common_site_config.append({"key": key, "value": value, "type": config_type})

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
			self.append("common_site_config_table", {"key": d.key, "value": value, "type": d.type})

		for d in bench_config:
			if d.key == "http_timeout":
				# http_timeout should be the only thing configurable in bench_config
				self.bench_config = json.dumps({"http_timeout": int(d.value)}, indent=4)
		if bench_config == []:
			self.bench_config = json.dumps({})

		self.save()

	@dashboard_whitelist()
	def update_environment_variable(self, environment_variables: dict):
		for key, value in environment_variables.items():
			is_updated = False
			for env_var in self.environment_variables:
				if env_var.key == key:
					if env_var.internal:
						frappe.throw(f"Environment variable {env_var.key} is internal and cannot be updated")
					else:
						env_var.value = value
						is_updated = True
			if not is_updated:
				self.append("environment_variables", {"key": key, "value": value, "internal": False})
		self.save()

	@dashboard_whitelist()
	def delete_environment_variable(self, key):
		updated_env_variables = []
		for env_var in self.environment_variables:
			if env_var.key != key or env_var.internal:
				updated_env_variables.append(env_var)
		self.environment_variables = updated_env_variables
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
		with suppress(AttributeError, RuntimeError):
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
			branch, repo = frappe.db.get_values("App Source", app.source, ("branch", "repository"))[0]
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
		if (
			self.max_gunicorn_workers
			and self.min_gunicorn_workers
			and self.max_gunicorn_workers < self.min_gunicorn_workers
		):
			frappe.throw(
				"Max Gunicorn Workers can't be less than Min Gunicorn Workers",
				frappe.ValidationError,
			)
		if (
			self.max_background_workers
			and self.min_background_workers
			and self.max_background_workers < self.min_background_workers
		):
			frappe.throw(
				"Max Background Workers can't be less than Min Background Workers",
				frappe.ValidationError,
			)

	def validate_feature_flags(self) -> None:
		if self.use_app_cache and not self.can_use_get_app_cache():
			frappe.throw(_("Use App Cache cannot be set, BENCH_VERSION must be 5.22.1 or later"))

	def can_use_get_app_cache(self) -> bool:
		version = find(
			self.dependencies,
			lambda x: x.dependency == "BENCH_VERSION",
		).version

		try:
			return sv.Version(version) in sv.SimpleSpec(">=5.22.1")
		except ValueError:
			return False

	@frappe.whitelist()
	def create_duplicate_deploy_candidate(self):
		return self.create_deploy_candidate([])

	@dashboard_whitelist()
	def redeploy(self):
		dc = self.create_duplicate_deploy_candidate()
		dc.schedule_build_and_deploy()

	@dashboard_whitelist()
	def initial_deploy(self):
		dc = self.create_deploy_candidate()
		dc.schedule_build_and_deploy()

	@frappe.whitelist()
	def create_deploy_candidate(
		self,
		apps_to_update=None,
		run_will_fail_check=False,
	) -> "DeployCandidate | None":
		if not self.enabled:
			return None

		apps = self.get_apps_to_update(apps_to_update)
		if apps_to_update is None:
			self.validate_dc_apps_against_rg(apps)

		dependencies = [{"dependency": d.dependency, "version": d.version} for d in self.dependencies]

		packages = [
			{
				"package_manager": p.package_manager,
				"package": p.package,
				"package_prerequisites": p.package_prerequisites,
				"after_install": p.after_install,
			}
			for p in self.packages
		]

		environment_variables = [{"key": v.key, "value": v.value} for v in self.environment_variables]

		# Create and deploy the DC
		new_dc: "DeployCandidate" = frappe.get_doc(
			{
				"doctype": "Deploy Candidate",
				"group": self.name,
				"apps": apps,
				"dependencies": dependencies,
				"packages": packages,
				"environment_variables": environment_variables,
			}
		)

		if run_will_fail_check:
			from press.press.doctype.deploy_candidate.validations import (
				check_if_update_will_fail,
			)

			check_if_update_will_fail(self, new_dc)

		new_dc.insert()
		return new_dc

	def validate_dc_apps_against_rg(self, dc_apps) -> None:
		app_map = {app["app"]: app for app in dc_apps}
		not_found = []
		for app in self.apps:
			if app.app in app_map:
				continue
			not_found.append(app.app)

		if not not_found:
			return

		msg = _("Following apps {0} not found. Potentially due to not approved App Releases.").format(
			not_found
		)
		frappe.throw(msg)

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
		out.apps = self.get_app_updates(last_deployed_bench.apps if last_deployed_bench else [])
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
				"Site",
				{"group": self.name, "status": ("in", ["Active", "Broken"])},
				["name", "server", "bench"],
			)
		]

		return out

	@dashboard_whitelist()
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

		if sites_in_group_details:
			Cluster = frappe.qb.DocType("Cluster")
			cluster_data = (
				frappe.qb.from_(Cluster)
				.select(Cluster.name, Cluster.title, Cluster.image)
				.where(Cluster.name.isin([site.cluster for site in sites_in_group_details]))
				.run(as_dict=True)
			)

			Plan = frappe.qb.DocType("Site Plan")
			plan_data = (
				frappe.qb.from_(Plan)
				.select(Plan.name, Plan.plan_title, Plan.price_inr, Plan.price_usd)
				.where(Plan.name.isin([site.plan for site in sites_in_group_details]))
				.run(as_dict=True)
			)

			ResourceTag = frappe.qb.DocType("Resource Tag")
			tag_data = (
				frappe.qb.from_(ResourceTag)
				.select(ResourceTag.tag_name, ResourceTag.parent)
				.where(ResourceTag.parent.isin([site.name for site in sites_in_group_details]))
				.run(as_dict=True)
			)

		cur_user_ssh_key = frappe.get_all(
			"User SSH Key", {"user": frappe.session.user, "is_default": 1}, limit=1
		)

		benches = [dn.name for dn in deployed_versions]
		benches_with_patches = frappe.get_all(
			"App Patch",
			fields=["bench"],
			filters={"bench": ["in", benches], "status": "Applied"},
			pluck="bench",
		)

		for version in deployed_versions:
			version.has_app_patch_applied = version.name in benches_with_patches
			version.has_ssh_access = version.is_ssh_proxy_setup and len(cur_user_ssh_key) > 0
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

	@dashboard_whitelist()
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

	@dashboard_whitelist()
	def send_change_team_request(self, team_mail_id: str, reason: str):
		"""Send email to team to accept bench transfer request"""

		if self.team != get_current_team():
			frappe.throw(
				"You should belong to the team owning the bench to initiate a bench ownership transfer."
			)

		if not frappe.db.exists("Team", {"user": team_mail_id, "enabled": 1}):
			frappe.throw("No Active Team record found.")

		old_team = frappe.db.get_value("Team", self.team, "user")

		if old_team == team_mail_id:
			frappe.throw(f"Bench is already owned by the team {team_mail_id}")

		team_change = frappe.get_doc(
			{
				"doctype": "Team Change",
				"document_type": "Release Group",
				"document_name": self.name,
				"to_team": frappe.db.get_value("Team", {"user": team_mail_id}),
				"from_team": self.team,
				"reason": reason or "",
			}
		).insert()

		key = frappe.generate_hash("Release Group Transfer Link", 20)
		minutes = 20
		frappe.cache.set_value(
			f"bench_transfer_data:{key}",
			(
				self.name,
				team_change.name,
			),
			expires_in_sec=minutes * 60,
		)

		link = get_url(f"/api/method/press.api.bench.confirm_bench_transfer?key={key}")

		if frappe.conf.developer_mode:
			print(f"Bench transfer link for {team_mail_id}\n{link}\n")

		frappe.sendmail(
			recipients=team_mail_id,
			subject="Transfer Bench Ownership Confirmation",
			template="transfer_team_confirmation",
			args={
				"name": self.title or self.name,
				"type": "bench",
				"old_team": old_team,
				"new_team": team_mail_id,
				"transfer_url": link,
				"minutes": minutes,
			},
		)

	@dashboard_whitelist()
	def generate_certificate(self):
		user_ssh_key = frappe.get_all(
			"User SSH Key",
			{"user": frappe.session.user, "is_default": True},
			pluck="name",
			limit=1,
		)

		if not user_ssh_key:
			frappe.throw(_("Please set a SSH key to generate certificate"))

		return frappe.get_doc(
			{
				"doctype": "SSH Certificate",
				"certificate_type": "User",
				"group": self.name,
				"user": frappe.session.user,
				"user_ssh_key": user_ssh_key[0],
				"validity": "6h",
			}
		).insert()

	@dashboard_whitelist()
	def get_certificate(self):
		user_ssh_key = frappe.db.get_all(
			"User SSH Key", {"user": frappe.session.user, "is_default": True}, pluck="name"
		)
		if not len(user_ssh_key):
			return False
		certificates = frappe.db.get_all(
			"SSH Certificate",
			{
				"user": frappe.session.user,
				"valid_until": [">", frappe.utils.now()],
				"group": self.name,
				"user_ssh_key": user_ssh_key[0],
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
		return frappe.utils.get_datetime(self.last_dependency_update) > self.last_dc_info.creation

	@property
	def deploy_in_progress(self):
		from press.press.doctype.bench.bench import TRANSITORY_STATES as BENCH_TRANSITORY
		from press.press.doctype.deploy_candidate.deploy_candidate import (
			TRANSITORY_STATES as DC_TRANSITORY,
		)

		if self.last_dc_info and self.last_dc_info.status in DC_TRANSITORY:
			return True

		if any(i["status"] in BENCH_TRANSITORY for i in self.last_benches_info):
			return True

		update_jobs = get_job_names(self.name, "Update Bench In Place", ["Pending", "Running"])
		if len(update_jobs):
			return True

		return False

	@property
	def status(self):
		active_benches = frappe.db.get_all(
			"Bench", {"group": self.name, "status": "Active"}, limit=1, order_by="creation desc"
		)
		return "Active" if active_benches else "Awaiting Deploy"

	@cached_property
	def last_dc_info(self) -> "LastDeployInfo | None":
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
		return None

	@cached_property
	def last_benches_info(self) -> "list[LastDeployInfo]":
		if not (name := (self.last_dc_info or {}).get("name")):
			return []

		b = frappe.qb.DocType("Bench")
		query = (
			frappe.qb.from_(b)
			.where(b.candidate == name)
			.select(b.name, b.status, b.creation)
			.orderby(b.creation, order=frappe.qb.desc)
			.limit(1)
		)
		return query.run(as_dict=True)

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
				current_source_branch = frappe.db.get_value("App Source", bench_app.source, "branch")
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
				AppRelease.public,
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
				latest_app_release = find(latest_app_releases, can_use_release)
				latest_app_releases = find_all(latest_app_releases, can_use_release)
			else:
				latest_app_release = find(latest_app_releases, lambda x: x.source == app.source)

			# No release exists for this source
			if not latest_app_release:
				continue

			bench_app = find(current_apps, lambda x: x.app == app.app)

			upcoming_release = latest_app_release.name if latest_app_release else bench_app.release
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

	def update_source(self, source: "AppSource", is_update: bool = False):
		self.remove_app_if_invalid(source)
		if is_update:
			update_rg_app_source(self, source)
		else:
			self.append("apps", {"source": source.name, "app": source.app})
		self.save()

	def remove_app_if_invalid(self, source: "AppSource"):
		"""
		Remove app if previously added app has an invalid
		repository URL and GitHub responds with a 404 when
		fetching the app information.
		"""
		matching_apps = [a for a in self.apps if a.app == source.app]
		if not matching_apps:
			return

		rg_app = matching_apps[0]
		value = frappe.get_value(
			"App Source",
			rg_app.source,
			["last_github_poll_failed", "last_github_response", "repository_url"],
			as_dict=True,
		)

		if value.repository_url == source.repository_url:
			return

		if not value.last_github_poll_failed or not value.last_github_response:
			return

		if '"Not Found"' not in value.last_github_response:
			return

		self.remove_app(source.app)

	@dashboard_whitelist()
	def change_app_branch(self, app: str, to_branch: str) -> None:
		current_app_source = self.get_app_source(app)

		# Already on that branch
		if current_app_source.branch == to_branch:
			frappe.throw(f"App already on branch {to_branch}!")

		required_app_source = frappe.get_all(
			"App Source",
			filters={"repository_url": current_app_source.repository_url, "branch": to_branch},
			or_filters={"team": current_app_source.team, "public": 1},
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
			required_app_source.github_installation_id = current_app_source.github_installation_id
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

	def get_marketplace_app_sources(self) -> list[str]:
		all_marketplace_sources = frappe.get_all("Marketplace App Version", pluck="source")
		return [app.source for app in self.apps if app.source in all_marketplace_sources]

	def get_clusters(self):
		"""Get unique clusters corresponding to self.servers"""
		servers = frappe.db.get_all("Release Group Server", {"parent": self.name}, pluck="server")
		return frappe.get_all("Server", {"name": ("in", servers)}, pluck="cluster", distinct=True)

	@dashboard_whitelist()
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

	def get_last_successful_candidate(self) -> "DeployCandidate":
		return frappe.get_last_doc("Deploy Candidate", {"status": "Success", "group": self.name})

	def get_last_deploy_candidate(self):
		try:
			dc: "DeployCandidate" = frappe.get_last_doc(
				"Deploy Candidate",
				{
					"status": ["!=", "Draft"],
					"group": self.name,
				},
			)
			return dc
		except frappe.DoesNotExistError:
			return None

	@frappe.whitelist()
	def add_server(self, server: str, deploy=False):
		self.append("servers", {"server": server, "default": False})
		self.save()
		if deploy:
			return self.get_last_successful_candidate()._create_deploy([server])
		return None

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

	@dashboard_whitelist()
	def add_app(self, app, is_update: bool = False):
		if isinstance(app, str):
			app = json.loads(app)

		if not (name := app.get("name")):
			return

		if frappe.db.exists("App", name):
			app_doc: "App" = frappe.get_doc("App", name)
		else:
			app_doc = new_app(name, app["title"])

		source = app_doc.add_source(
			self.version,
			app["repository_url"],
			app["branch"],
			self.team,
			app.get("github_installation_id", None),
		)
		self.update_source(source, is_update)

	@dashboard_whitelist()
	def remove_app(self, app: str):
		"""Remove app from release group"""

		app_doc_to_remove = find(self.apps, lambda x: x.app == app)
		if app_doc_to_remove:
			self.remove(app_doc_to_remove)

		self.save()
		return app

	@dashboard_whitelist()
	def fetch_latest_app_update(self, app: str):
		app_source = self.get_app_source(app)
		app_source.create_release(force=True)

	@frappe.whitelist()
	def archive(self):
		benches = frappe.get_all("Bench", filters={"group": self.name, "status": "Active"}, pluck="name")
		for bench in benches:
			frappe.get_doc("Bench", bench).archive()

		new_name = f"{self.title}.archived"
		self.title = append_number_if_name_exists("Release Group", new_name, "title", separator=".")
		self.enabled = 0
		self.save()

		frappe.db.delete("Press Role Permission", {"release_group": self.name})

	@dashboard_whitelist()
	def delete(self) -> None:
		# Note: using delete instead of archive to avoid client api fetching the doc again

		self.archive()

	def set_default_app_cache_flags(self):
		if self.use_app_cache:
			return

		if not frappe.db.get_single_value("Press Settings", "use_app_cache"):
			return

		if not self.can_use_get_app_cache():
			return

		self.use_app_cache = 1
		self.compress_app_cache = frappe.db.get_single_value(
			"Press Settings",
			"compress_app_cache",
		)

	def set_default_delta_builds_flags(self):
		if not frappe.db.get_single_value("Press Settings", "use_delta_builds"):
			return

		self.use_delta_builds = 0

	def is_version_14_or_higher(self):
		return frappe.get_cached_value("Frappe Version", self.version, "number") >= 14


@redis_cache(ttl=60)
def are_builds_suspended() -> bool:
	return is_suspended()


def new_release_group(title, version, apps, team=None, cluster=None, saas_app="", server=None):
	if cluster:
		if not server:
			restricted_release_group_names = frappe.db.get_all(
				"Site Plan Release Group",
				pluck="release_group",
				filters={"parenttype": "Site Plan", "parentfield": "release_groups"},
				distinct=True,
			)
			restricted_server_names = frappe.db.get_all(
				"Release Group Server",
				pluck="server",
				filters={
					"parenttype": "Release Group",
					"parentfield": "servers",
					"parent": ("in", restricted_release_group_names),
				},
				distinct=True,
			)
			server = frappe.get_all(
				"Server",
				{
					"status": "Active",
					"cluster": cluster,
					"use_for_new_benches": True,
					"name": ("not in", restricted_server_names),
				},
				pluck="name",
				limit=1,
			)[0]
		servers = [{"server": server}]
	elif server:
		servers = [{"server": server}]
	else:
		servers = []
	return frappe.get_doc(
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


def get_status(name):
	return (
		"Active"
		if frappe.get_all("Bench", {"group": name, "status": "Active"}, limit=1, order_by="creation desc")
		else "Awaiting Deploy"
	)


def prune_servers_without_sites():
	rg_servers = frappe.qb.DocType("Release Group Server")
	rg = frappe.qb.DocType("Release Group")
	groups_with_multiple_servers = (
		frappe.qb.from_(rg_servers)
		.inner_join(rg)
		.on(rg.name == rg_servers.parent)
		.where(rg.enabled == 1)
		.where(rg.public == 0)
		.where(rg.central_bench == 0)
		.where(rg.team != "team@erpnext.com")
		.where(
			rg.modified < frappe.utils.add_to_date(None, days=-7)
		)  # use this timestamp to assume server added time
		.groupby(rg_servers.parent)
		.having(Count("*") > 1)
		.select(rg_servers.parent)
		.run(as_dict=False)
	)
	groups_with_multiple_servers = [x[0] for x in groups_with_multiple_servers]
	groups_with_multiple_servers = frappe.get_all(
		"Release Group Server",
		filters={"parent": ("in", groups_with_multiple_servers)},
		fields=["parent", "server"],
		order_by="parent",
		as_list=True,
	)

	from press.press.doctype.bench.bench import (
		get_scheduled_version_upgrades,
		get_unfinished_site_migrations,
	)

	for group, server in groups_with_multiple_servers:
		sites = frappe.get_all(
			"Site",
			{"status": ("!=", "Archived"), "group": group, "server": server},
			["name"],
		)
		if not sites:
			benches = frappe.get_all(
				"Bench",
				{"group": group, "server": server, "status": "Active"},
				["name", "server", "group"],
			)
			for bench in benches:
				if get_unfinished_site_migrations(bench.name) or get_scheduled_version_upgrades(bench):
					continue
			frappe.db.delete("Release Group Server", {"parent": group, "server": server})
			frappe.db.commit()


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Release Group")


def can_use_release(app_src):
	if not app_src.public:
		return True

	return app_src.status == "Approved"


def update_rg_app_source(rg: "ReleaseGroup", source: "AppSource"):
	for app in rg.apps:
		if app.app == source.app:
			app.source = source.name
			break


def get_job_names(rg: str, job_type: str, job_status: list[str]):
	b = frappe.qb.DocType("Bench")
	aj = frappe.qb.DocType("Agent Job")

	jobs = (
		frappe.qb.from_(b)
		.inner_join(aj)
		.on(b.name == aj.bench)
		.where(b.group == rg)
		.where(aj.job_type == job_type)
		.where(aj.status.isin(job_status))
		.select(aj.name)
		.orderby(aj.modified, order=frappe.query_builder.Order.desc)
	).run()

	return [j[0] for j in jobs]


def get_config_type(value: Any):
	if isinstance(value, (dict, list)):
		return "JSON"

	if isinstance(value, bool):
		return "Boolean"

	if isinstance(value, (int, float)):
		return "Number"

	return "String"


def get_formatted_config_value(config_type: str, value: Any, key: str, name: str):
	if config_type == "Number":
		return flt(value)

	if config_type == "Boolean":
		return bool(sbool(value))

	if config_type == "JSON":
		return frappe.parse_json(value)

	if config_type == "Password" and value == "*******":
		return frappe.get_value("Site Config", {"key": key, "parent": name}, "value")

	return value
