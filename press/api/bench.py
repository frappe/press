# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import re
from collections import OrderedDict
from typing import TYPE_CHECKING

import frappe
import requests
from frappe.core.utils import find, find_all
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import flt, sbool

from press.api.github import branches, get_access_token
from press.api.site import protected
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.app_patch.app_patch import create_app_patch
from press.press.doctype.bench_update.bench_update import get_bench_update
from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import (
	fail_and_redeploy as fail_and_redeploy_build,
)
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import fail_remote_job
from press.press.doctype.deploy_candidate_build.deploy_candidate_build import redeploy as redeploy_candidate
from press.press.doctype.marketplace_app.marketplace_app import (
	get_total_installs_by_app,
)
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)
from press.press.doctype.team.team import get_child_team_members
from press.utils import (
	get_app_tag,
	get_client_blacklisted_keys,
	get_current_team,
	unique,
)

if TYPE_CHECKING:
	from press.press.doctype.app_source.app_source import AppSource
	from press.press.doctype.bench.bench import Bench
	from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate
	from press.press.doctype.deploy_candidate_build.deploy_candidate_build import DeployCandidateBuild


@frappe.whitelist()
def new(bench):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new bench because your account is disabled")

	if exists(bench["title"]):
		frappe.throw("A bench exists with the same name")

	if bench["server"] and not (
		frappe.session.data.user_type == "System User"
		or frappe.db.get_value("Server", bench["server"], "team") == team.name
	):
		frappe.throw("You can only create benches on your servers")

	apps = [{"app": app["name"], "source": app["source"]} for app in bench["apps"]]
	group = new_release_group(
		bench["title"],
		bench["version"],
		apps,
		team.name,
		bench["cluster"],
		bench["saas_app"] if frappe.db.exists("Saas App", bench["saas_app"]) else "",
		bench["server"],
	)
	return group.name


@frappe.whitelist()
@protected("Release Group")
def get(name):
	group = frappe.get_doc("Release Group", name)
	return {
		"name": group.name,
		"title": group.title,
		"team": group.team,
		"version": group.version,
		"status": get_group_status(name),
		"last_updated": group.modified,
		"creation": group.creation,
		"saas_app": group.saas_app or "",
		"public": group.public,
		"no_sites": frappe.db.count("Site", {"group": group.name, "status": "Active"}),
		"bench_tags": [{"name": x.tag, "tag": x.tag_name} for x in group.tags],
		"tags": frappe.get_all(
			"Press Tag", {"team": group.team, "doctype_name": "Release Group"}, ["name", "tag"]
		),
	}


def get_group_status(name):
	active_benches = frappe.get_all(
		"Bench", {"group": name, "status": "Active"}, limit=1, order_by="creation desc"
	)

	return "Active" if active_benches else "Awaiting Deploy"


@frappe.whitelist()
def all(server=None, bench_filter=None):
	if bench_filter is None:
		bench_filter = {"status": "", "tag": ""}

	team = get_current_team()
	child_teams = [team.name for team in get_child_team_members(team)]
	teams = [team, *child_teams]

	group = frappe.qb.DocType("Release Group")
	site = frappe.qb.DocType("Site")
	query = (
		frappe.qb.from_(group)
		.left_join(site)
		.on((site.group == group.name) & (site.status != "Archived"))
		.where((group.enabled == 1) & (group.public == 0))
		.where((group.team).isin(teams))
		.groupby(group.name)
		.select(
			frappe.query_builder.functions.Count(site.name).as_("number_of_sites"),
			group.name,
			group.title,
			group.version,
			group.creation,
		)
		.orderby(group.title, order=frappe.qb.desc)
	)

	bench = frappe.qb.DocType("Bench")
	if bench_filter["status"] == "Active":
		query = query.inner_join(bench).on(group.name == bench.group)
	elif bench_filter["status"] == "Awaiting Deploy":
		group_names = frappe.get_all("Bench", {"status": "Active"}, pluck="group", distinct=True)
		query = query.inner_join(bench).on(group.name.notin(group_names))
	if bench_filter["tag"]:
		press_tag = frappe.qb.DocType("Resource Tag")
		query = query.inner_join(press_tag).on(
			(press_tag.tag_name == bench_filter["tag"]) & (press_tag.parent == group.name)
		)

	if server:
		group_server = frappe.qb.DocType("Release Group Server")
		query = (
			query.inner_join(group_server)
			.on(group_server.parent == group.name)
			.where(group_server.server == server)
		)
	private_groups = query.run(as_dict=True)

	if not private_groups:
		return []

	app_counts = get_app_counts_for_groups([rg.name for rg in private_groups])
	for group in private_groups:
		group.tags = frappe.get_all("Resource Tag", {"parent": group.name}, pluck="tag_name")
		group.number_of_apps = app_counts[group.name]
		group.status = get_group_status(group.name)

	return private_groups


@frappe.whitelist()
def bench_tags():
	team = get_current_team()
	return frappe.get_all("Press Tag", {"team": team, "doctype_name": "Release Group"}, pluck="tag")


def get_app_counts_for_groups(rg_names):
	rg_app = frappe.qb.DocType("Release Group App")

	app_counts = (
		frappe.qb.from_(rg_app)
		.where(rg_app.parent.isin(rg_names))
		.groupby(rg_app.parent)
		.select(
			rg_app.parent,
			frappe.query_builder.functions.Count("*"),
		)
		.run()
	)

	app_counts_map = {}
	for rg_name, app_count in app_counts:
		app_counts_map[rg_name] = app_count

	return app_counts_map


@frappe.whitelist()
def exists(title):
	team = get_current_team()
	return bool(frappe.db.exists("Release Group", {"title": title, "team": team, "enabled": True}))


@frappe.whitelist()
def get_default_apps():
	press_settings = frappe.get_single("Press Settings")
	default_apps = press_settings.get_default_apps()

	versions, rows = get_app_versions_list()

	version_based_default_apps = {v.version: [] for v in versions}

	for app in default_apps:
		for row in filter(lambda x: x.app == app, rows):
			version_based_default_apps[row.version].append(row)

	return version_based_default_apps


def get_app_versions_list(only_frappe=False):
	AppSource = frappe.qb.DocType("App Source")
	FrappeVersion = frappe.qb.DocType("Frappe Version")
	AppSourceVersion = frappe.qb.DocType("App Source Version")
	rows = (
		frappe.qb.from_(AppSourceVersion)
		.left_join(AppSource)
		.on(AppSourceVersion.parent == AppSource.name)
		.left_join(FrappeVersion)
		.on(AppSourceVersion.version == FrappeVersion.name)
		.where((AppSource.enabled == 1) & (AppSource.public == 1) & (FrappeVersion.public == 1))
		.select(
			FrappeVersion.name.as_("version"),
			FrappeVersion.status,
			FrappeVersion.default,
			AppSource.name.as_("source"),
			AppSource.app,
			AppSource.repository_url,
			AppSource.repository,
			AppSource.repository_owner,
			AppSource.branch,
			AppSource.app_title.as_("title"),
			AppSource.frappe,
		)
		.orderby(AppSource.creation)
	)

	if only_frappe:
		rows = rows.where(AppSource.frappe == 1)

	rows = rows.run(as_dict=True)

	version_list = unique(rows, lambda x: x.version)

	return version_list, rows


@frappe.whitelist()
def options():
	version_list, rows = get_app_versions_list(only_frappe=True)
	approved_apps = frappe.get_all("Marketplace App", filters={"frappe_approved": 1}, pluck="app")

	versions = []
	for d in version_list:
		version_dict = {"name": d.version, "status": d.status, "default": d.default}
		version_rows = find_all(rows, lambda x: x.version == d.version)
		app_list = frappe.utils.unique([row.app for row in version_rows])
		app_list = sorted(app_list, key=lambda x: x not in approved_apps)

		for app in app_list:
			app_rows = find_all(version_rows, lambda x: x.app == app)
			app_dict = {"name": app, "title": app_rows[0].title}

			for source in app_rows:
				source_dict = {
					"name": source.source,
					"repository_url": source.repository_url,
					"branch": source.branch,
					"repository": source.repository,
					"repository_owner": source.repository_owner,
				}
				app_dict.setdefault("sources", []).append(source_dict)

			app_dict["source"] = app_dict["sources"][0]
			version_dict.setdefault("apps", []).append(app_dict)
		versions.append(version_dict)

	clusters = Cluster.get_all_for_new_bench()

	if not versions:
		frappe.throw("Only enabled and public app sources will reflect here!")

	return {"versions": versions, "clusters": clusters}


@frappe.whitelist()
@protected("Release Group")
def bench_config(name):
	rg = frappe.get_doc("Release Group", name)

	common_site_config = [
		{"key": config.key, "value": config.value, "type": config.type}
		for config in rg.common_site_config_table
		if not config.internal
	]

	bench_config = frappe.parse_json(rg.bench_config)
	if bench_config.get("http_timeout"):
		bench_config = [
			frappe._dict(
				key="http_timeout",
				value=bench_config.get("http_timeout"),
				type="Number",
				internal=False,
			)
		]
	else:
		bench_config = []

	config = common_site_config + bench_config

	secret_keys = frappe.get_all("Site Config Key", filters={"type": "Password"}, pluck="key")
	for c in config:
		if c["key"] in secret_keys:
			c["value"] = "*******"
			c["type"] = "Password"
	return config


@frappe.whitelist()
@protected("Release Group")
def update_config(name, config):
	sanitized_common_site_config, sanitized_bench_config = [], []
	bench_config_keys = ["http_timeout"]

	config = frappe.parse_json(config)
	config = [frappe._dict(c) for c in config]

	for c in config:
		if c.key in get_client_blacklisted_keys():
			continue

		if frappe.db.exists("Site Config Key", c.key):
			c.type = frappe.db.get_value("Site Config Key", c.key, "type")
		format_config_value(name, c)

		if c.key in bench_config_keys:
			sanitized_bench_config.append(c)
		else:
			sanitized_common_site_config.append(c)

	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	rg.update_config_in_release_group(sanitized_common_site_config, sanitized_bench_config)
	rg.update_benches_config()
	return list(filter(lambda x: not x.internal, rg.common_site_config_table))


def format_config_value(group: str, c: frappe._dict):
	if c.type == "Number":
		c.value = flt(c.value)
	elif c.type == "Boolean":
		c.value = bool(sbool(c.value))
	elif c.type == "JSON":
		c.value = frappe.parse_json(c.value)
	elif c.type == "Password" and c.value == "*******":
		c.value = frappe.get_value("Site Config", {"key": c.key, "parent": group}, "value")


@frappe.whitelist()
@protected("Release Group")
def dependencies(name: str):
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	active_dependencies = [{"key": d.dependency, "value": d.version} for d in rg.dependencies]
	supported_dependencies = frappe.db.get_all(
		"Bench Dependency Version",
		{"supported_frappe_version": rg.version},
		["parent as `key`", "version as `value`"],
	)

	bench_dependencies = frappe.get_all("Bench Dependency", ["name", "title", "internal"])

	return {
		"active_dependencies": active_dependencies,
		"supported_dependencies": list(
			# deduplicate dependencies
			{d["value"]: d for d in supported_dependencies + active_dependencies}.values()
		),
		"dependency_title": {d["name"]: d["title"] for d in bench_dependencies},
		"internal_dependencies": [d["name"] for d in bench_dependencies if d["internal"]],
		"update_available": rg.dependency_update_pending,
	}


@frappe.whitelist()
@protected("Release Group")
def update_dependencies(name: str, dependencies: str):
	dependencies = frappe.parse_json(dependencies)
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	if len(rg.dependencies) != len(dependencies):
		frappe.throw("Need all required dependencies")
	if diff := set([d["key"] for d in dependencies]) - set(d.dependency for d in rg.dependencies):
		frappe.throw("Invalid dependencies: " + ", ".join(diff))
	for dep, new in zip(
		sorted(rg.dependencies, key=lambda x: x.dependency),
		sorted(dependencies, key=lambda x: x["key"]),
		strict=False,
	):
		if dep.dependency != new["key"]:
			frappe.throw(f"Invalid dependency: {new['key']}")
		if not re.match(r"^\d+\.\d+\.*\d*$", new["value"]):
			frappe.throw(f"Invalid version for {new['key']}")
		dep.version = new["value"]
	rg.save()


@frappe.whitelist()
@protected("Release Group")
def apps(name):
	group = frappe.get_doc("Release Group", name)
	apps = []
	deployed_apps = frappe.db.get_all(
		"Bench",
		filters={"group": group.name, "status": ("!=", "Archived")},
		fields=["`tabBench App`.app"],
		pluck="app",
	)
	deployed_apps = unique(deployed_apps)
	updates = deploy_information(name)

	latest_bench = frappe.get_all(
		"Bench",
		filters={"group": group.name, "status": "Active"},
		order_by="creation desc",
		limit=1,
		pluck="name",
	)
	if latest_bench:
		latest_bench = latest_bench[0]
	else:
		latest_bench = None

	latest_deployed_apps = frappe.get_all(
		"Bench",
		filters={"name": latest_bench},
		fields=["`tabBench App`.app", "`tabBench App`.hash"],
	)

	for app in group.apps:
		source = frappe.get_doc("App Source", app.source)
		app = frappe.get_doc("App", app.app)
		update_available = updates["update_available"] and find(
			updates.apps, lambda x: x["app"] == app.name and x["update_available"]
		)

		latest_deployed_app = find(latest_deployed_apps, lambda x: x.app == app.name)
		hash = latest_deployed_app.hash if latest_deployed_app else None
		tag = get_app_tag(source.repository, source.repository_owner, hash)

		marketplace_app_title = frappe.db.get_value("Marketplace App", app.name, "title")
		app_title = marketplace_app_title or app.title

		apps.append(
			{
				"name": app.name,
				"frappe": app.frappe,
				"title": app_title,
				"branch": source.branch,
				"repository_url": source.repository_url,
				"repository": source.repository,
				"repository_owner": source.repository_owner,
				"tag": tag,
				"hash": hash,
				"deployed": app.name in deployed_apps,
				"update_available": bool(update_available),
				"last_github_poll_failed": source.last_github_poll_failed,
			}
		)
	return apps


@frappe.whitelist()
@protected("Release Group")
def installable_apps(name):
	release_group = frappe.get_doc("Release Group", name)
	installed_apps = [app.app for app in release_group.apps]
	versions = options()["versions"]
	version = find(versions, lambda x: x["name"] == release_group.version)
	apps = version["apps"] if version else []
	return [app for app in apps if app["name"] not in installed_apps]


@frappe.whitelist()
@protected("Release Group")
def all_apps(name):
	"""Return all apps in the marketplace that are not installed in the release group for adding new apps"""

	release_group = frappe.get_doc("Release Group", name)
	installed_apps = [app.app for app in release_group.apps]
	marketplace_apps = frappe.get_all(
		"Marketplace App",
		filters={"status": "Published", "app": ("not in", installed_apps)},
		fields=["name", "title", "image", "app"],
	)

	if not marketplace_apps:
		return []

	AppSource = frappe.qb.DocType("App Source")
	AppSourceVersion = frappe.qb.DocType("App Source Version")
	marketplace_app_sources = (
		frappe.qb.from_(AppSource)
		.left_join(AppSourceVersion)
		.on(AppSourceVersion.parent == AppSource.name)
		.select(
			AppSource.name,
			AppSource.branch,
			AppSource.repository,
			AppSource.repository_owner,
			AppSource.app,
			AppSourceVersion.version,
		)
		.where(
			(AppSource.app.isin([app.app for app in marketplace_apps]))
			& (AppSource.enabled == 1)
			& (AppSource.public == 1)
		)
	).run(as_dict=1)

	total_installs_by_app = get_total_installs_by_app()

	for app in marketplace_apps:
		app["sources"] = find_all(
			list(filter(lambda x: x.version == release_group.version, marketplace_app_sources)),
			lambda x: x.app == app.app,
		)
		# for fetching repo details for incompatible apps
		app_source = find(marketplace_app_sources, lambda x: x.app == app.app)
		app["repo"] = f"{app_source.repository_owner}/{app_source.repository}" if app_source else None
		app["total_installs"] = total_installs_by_app.get(app["name"], 0)

	return marketplace_apps


@frappe.whitelist()
@protected("Release Group")
def fetch_latest_app_update(name, app):
	frappe.get_doc("Release Group", name).fetch_latest_app_update(app)


@frappe.whitelist()
@protected("Release Group")
def add_app(name, source, app):
	add_apps(name, [{"app": app, "source": source}])


@frappe.whitelist()
@protected("Release Group")
def add_apps(name, apps):
	release_group: "ReleaseGroup" = frappe.get_doc("Release Group", name)
	for app in apps:
		app_name, source = app.values()
		release_group.update_source(frappe._dict(name=source, app=app_name))


@frappe.whitelist()
@protected("Release Group")
def remove_app(name, app):
	return frappe.get_doc("Release Group", name).remove_app(app)


@frappe.whitelist()
@protected("Release Group")
def versions(name):
	Bench = frappe.qb.DocType("Bench")
	Server = frappe.qb.DocType("Server")
	deployed_versions = (
		frappe.qb.from_(Bench)
		.left_join(Server)
		.on(Server.name == Bench.server)
		.where((Bench.group == name) & (Bench.status != "Archived"))
		.groupby(Bench.name)
		.select(Bench.name, Bench.status, Bench.is_ssh_proxy_setup, Server.proxy_server)
		.orderby(Bench.creation, order=frappe.qb.desc)
		.run(as_dict=True)
	)

	rg_version = frappe.db.get_value("Release Group", name, "version")

	sites_in_group_details = frappe.db.get_all(
		"Site",
		filters={
			"group": name,
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
	else:
		cluster_data = plan_data = tag_data = {}

	for version in deployed_versions:
		version.sites = find_all(sites_in_group_details, lambda x: x.bench == version.name)
		version.version = rg_version
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
@protected("Bench")
def get_installed_apps_in_version(name):
	apps = frappe.db.get_all(
		"Bench App",
		{"parent": name},
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
@protected("Bench")
def get_processes(name):
	bench: "Bench" = frappe.get_doc("Bench", name)
	if bench.status != "Active" and bench.status != "Broken":
		return []

	return bench.supervisorctl_status()


@frappe.whitelist()
@protected("Release Group")
def candidates(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	# TODO: Status is redundant here.
	result = frappe.get_all(
		"Deploy Candidate",
		["name", "creation", "status"],
		{"group": filters["group"], "status": ("!=", "Draft")},
		order_by=order_by or "creation desc",
		start=limit_start,
		limit=limit_page_length,
	)
	candidates = OrderedDict()
	for d in result:
		candidates.setdefault(d.name, {})
		candidates[d.name].update(d)
		dc_apps = frappe.get_all(
			"Deploy Candidate App",
			filters={"parent": d.name},
			pluck="app",
			order_by="creation desc",
		)
		candidates[d.name]["apps"] = dc_apps

	return candidates.values()


@frappe.whitelist()
def candidate(name):
	if not name:
		return None

	candidate: DeployCandidate = frappe.get_doc("Deploy Candidate", name)
	jobs = []
	deploys = frappe.get_all("Deploy", {"candidate": name}, limit=1)
	if deploys:
		deploy = frappe.get_doc("Deploy", deploys[0].name)
		for bench in deploy.benches:
			if not bench.bench:
				continue
			job = frappe.get_all(
				"Agent Job",
				["name", "status", "end", "duration", "bench"],
				{"bench": bench.bench, "job_type": "New Bench"},
				limit=1,
			) or [{}]
			jobs.append(job[0])

	# Taking the latest Build for that Candidate
	build_name = frappe.get_value("Deploy Candidate Build", {"deploy_candidate": name})
	build: DeployCandidateBuild = frappe.get_doc("Deploy Candidate Build", build_name)

	return {
		"name": candidate.name,
		"status": build.status,
		"creation": build.creation,
		"deployed": False,
		"build_steps": build.build_steps,
		"build_start": build.build_start,
		"build_end": build.build_end,
		"build_duration": build.build_duration,
		"apps": build.candidate.apps,
		"jobs": jobs,
	}


@frappe.whitelist()
@protected("Release Group")
def deploy_information(name):
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	return rg.deploy_information()


@frappe.whitelist()
@protected("Release Group")
def deploy(name, apps):
	team = get_current_team(True)
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)

	if rg.team != team.name:
		frappe.throw("Bench can only be deployed by the bench owner", exc=frappe.PermissionError)

	if rg.deploy_in_progress:
		frappe.throw("A deploy for this bench is already in progress")

	candidate = rg.create_deploy_candidate(apps)
	deploy_candidate_build = candidate.schedule_build_and_deploy()

	return deploy_candidate_build["name"]


def validate_app_hashes(apps: list[dict[str, str]]):
	"""Ensure none of them are yanked"""
	hashes = []
	for app in apps:
		if not app.get("release") or not app.get("hash"):
			frappe.throw("Each app must have a release and hash to run deploy and update!")
		else:
			hashes.append(app.get("hash"))

	YankedAppRelease = frappe.qb.DocType("Yanked App Release")
	has_yanked_apps = (
		frappe.qb.from_(YankedAppRelease)
		.where(YankedAppRelease.hash.isin(hashes))
		.select(YankedAppRelease.hash)
		.run(as_dict=True)
	)

	if has_yanked_apps:
		frappe.throw(
			"Invalid app version selected for deploy: " + ", ".join([app.hash for app in has_yanked_apps])
		)


@frappe.whitelist()
@protected("Release Group")
def deploy_and_update(
	name: str,
	apps: list,
	sites: list | None = None,
	run_will_fail_check: bool = True,
):
	validate_app_hashes(apps)

	# Returns name of the Deploy Candidate that is running the build
	return get_bench_update(
		name,
		apps,
		sites,
		False,
	).deploy(run_will_fail_check)


@frappe.whitelist()
@protected("Release Group")
def update_inplace(
	name: str,
	apps: list,
	sites: list,
):
	validate_app_hashes(apps)
	# Returns name of the Agent Job name that runs the inplace update
	return get_bench_update(
		name,
		apps,
		sites,
		True,
	).update_inplace()


@frappe.whitelist()
@protected("Release Group")
def create_deploy_candidate(name, apps_to_ignore=None):
	apps_to_ignore = [] if apps_to_ignore is None else apps_to_ignore
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	return rg.create_deploy_candidate(apps_to_ignore)


@frappe.whitelist()
@protected("Release Group")
def jobs(filters=None, order_by=None, limit_start=None, limit_page_length=None):
	benches = frappe.get_all("Bench", {"group": filters["name"]}, pluck="name")
	if benches:
		jobs = frappe.get_all(
			"Agent Job",
			fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
			filters={"bench": ("in", benches)},
			order_by=order_by or "creation desc",
			start=limit_start,
			limit=limit_page_length,
			ignore_ifnull=True,
		)
		for job in jobs:
			job["status"] = "Pending" if job["status"] == "Undelivered" else job["status"]
	else:
		jobs = []
	return jobs


@frappe.whitelist()
@protected("Release Group")
def running_jobs(name):
	benches = frappe.get_all("Bench", {"group": name}, pluck="name")
	jobs = frappe.get_all(
		"Agent Job",
		filters={"status": ("in", ("Pending", "Running")), "bench": ("in", benches)},
	)
	return [job_detail(job.name) for job in jobs]


@frappe.whitelist()
@protected("Release Group")
def recent_deploys(name):
	return frappe.get_all(
		"Deploy Candidate",
		["name", "creation"],
		{"group": name, "status": ("!=", "Draft")},
		order_by="creation desc",
		limit=3,
	)


@frappe.whitelist()
@protected("Release Group")
def change_branch(name: str, app: str, to_branch: str):
	"""Switch to `to_branch` for `app` in release group `name`"""
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	rg.change_app_branch(app, to_branch)


@frappe.whitelist()
@protected("Release Group")
def branch_list(name: str, app: str) -> list[dict]:
	"""Return a list of git branches available for the `app`"""
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	app_source = rg.get_app_source(app)

	installation_id = app_source.github_installation_id
	repo_owner = app_source.repository_owner
	repo_name = app_source.repository

	marketplace_app = frappe.get_all("Marketplace App", filters={"app": app}, pluck="name", limit=1)

	if marketplace_app and app_source.public and (not belongs_to_current_team(marketplace_app[0])):
		return get_branches_for_marketplace_app(app, marketplace_app[0], app_source)

	return branches(repo_owner, repo_name, installation_id)


@frappe.whitelist()
@protected("Release Group")
def validate_branch(name: str, app: str, branch: str):
	"""Validates whether a branch is available for the `app`"""
	release_group = frappe.get_doc("Release Group", name)
	app_source = release_group.get_app_source(app)

	token = get_access_token(app_source.github_installation_id)

	if token:
		headers = {
			"Authorization": f"token {token}",
		}
	else:
		headers = {}

	response = requests.get(
		f"https://api.github.com/repos/{app_source.repository_owner}/{app_source.repository}/branches/{branch}",
		headers=headers,
		timeout=10,
	)

	if response.ok:
		return response.json()
	frappe.throw("Error validating branch from GitHub: " + response.text)
	return None


def get_branches_for_marketplace_app(app: str, marketplace_app: str, app_source: AppSource) -> list[dict]:
	"""Return list of branches allowed for this `marketplace` app"""
	branch_set = set()
	marketplace_app = frappe.get_doc("Marketplace App", marketplace_app)

	for marketplace_app_source in marketplace_app.sources:
		app_source = frappe.get_doc("App Source", marketplace_app_source.source)
		branch_set.add(app_source.branch)

	# Also, append public source branches
	repo_owner = app_source.repository_owner
	repo_name = app_source.repository

	public_app_sources = frappe.get_all(
		"App Source",
		filters={
			"app": app,
			"repository_owner": repo_owner,
			"repository": repo_name,
			"public": True,
		},
		pluck="branch",
	)
	branch_set.update(public_app_sources)

	branch_list = sorted(list(branch_set))
	return [{"name": b} for b in branch_list]


def belongs_to_current_team(app: str) -> bool:
	"""Does the Marketplace App `app` belong to current team"""
	current_team = get_current_team()
	marketplace_app = frappe.get_doc("Marketplace App", app)

	return marketplace_app.team == current_team


@frappe.whitelist()
@protected("Release Group")
def regions(name):
	rg = frappe.get_doc("Release Group", name)
	cluster_names = rg.get_clusters()
	return frappe.get_all(
		"Cluster", fields=["name", "title", "image"], filters={"name": ("in", cluster_names)}
	)


@frappe.whitelist()
@protected("Release Group")
def available_regions(name):
	rg = frappe.get_doc("Release Group", name)
	cluster_names = rg.get_clusters()
	return Cluster.get_all_for_new_bench({"name": ("not in", cluster_names)})


@frappe.whitelist()
@protected("Release Group")
def add_region(name, region):
	frappe.get_doc("Release Group", name).add_region(region)


@frappe.whitelist()
@protected("Release Group")
def archive(name):
	benches = frappe.get_all("Bench", filters={"group": name, "status": "Active"}, pluck="name")

	for bench in benches:
		frappe.get_doc("Bench", bench).archive()

	group = frappe.get_doc("Release Group", name)
	new_name = f"{group.title}.archived"
	group.title = append_number_if_name_exists("Release Group", new_name, "title", separator=".")
	group.enabled = 0
	group.save()


@frappe.whitelist()
@protected("Bench")
def restart(name):
	frappe.get_doc("Bench", name).restart()


@frappe.whitelist()
@protected("Bench")
def rebuild(name):
	frappe.get_doc("Bench", name).rebuild()


@frappe.whitelist()
@protected("Bench")
def update(name):
	frappe.get_doc("Bench", name).update_all_sites()


@frappe.whitelist()
@protected("Release Group")
def update_all_sites(name):
	benches = frappe.get_all("Bench", {"group": name, "status": "Active"})
	for bench in benches:
		frappe.get_cached_doc("Bench", bench).update_all_sites()


@frappe.whitelist()
@protected("Release Group")
def logs(name, bench):
	from press.agent import AgentRequestSkippedException

	if frappe.db.get_value("Bench", bench, "group") != name:
		return []

	try:
		return frappe.get_doc("Bench", bench).server_logs
	except AgentRequestSkippedException:
		return []


@frappe.whitelist()
@protected("Release Group")
def log(name, bench, log):
	if frappe.db.get_value("Bench", bench, "group") != name:
		frappe.throw(f"Release Group name {name} does not match Bench Release Group")
	return frappe.get_doc("Bench", bench).get_server_log(log)


@frappe.whitelist()
@protected("Release Group")
def certificate(name):
	return frappe.get_doc("Release Group", name).get_certificate()


@frappe.whitelist()
@protected("Release Group")
def generate_certificate(name):
	return frappe.get_doc("Release Group", name).generate_certificate()


@frappe.whitelist()
@protected("Release Group")
def get_title_and_creation(name):
	result = frappe.db.get_value("Release Group", name, ["title", "creation"], as_dict=True)
	server = frappe.get_all(
		"Release Group Server", {"parent": name}, pluck="server", order_by="idx asc", limit=1
	)[0]
	result["team"] = frappe.db.get_value("Server", server, "team")
	return result


@frappe.whitelist()
@protected("Release Group")
def rename(name, title):
	return frappe.db.set_value("Release Group", name, "title", title)


@frappe.whitelist()
@protected("Release Group")
def apply_patch(release_group: str, app: str, patch_config: dict) -> list[str]:
	team = get_current_team()

	return create_app_patch(
		release_group,
		app,
		team,
		patch_config,
	)


@frappe.whitelist()
@protected("Release Group")
def fail_build(dn: str):
	failed = fail_remote_job(dn)

	if not failed:
		frappe.throw("No running job found!")


@frappe.whitelist()
@protected("Release Group")
def fail_and_redeploy(name: str, dc_name: str):
	res = fail_and_redeploy_build(dc_name)

	# If failed error is True
	if res.get("error"):
		return None

	# New Deploy Candidate name
	return res.get("message")


@frappe.whitelist()
@protected("Release Group")
def show_app_versions(name: str, dc_name: str) -> dict[str, str]:
	"""Get app versions from the deploy candidate"""
	candidate = frappe.db.get_value("Deploy Candidate Build", dc_name, "deploy_candidate")
	deploy_candidate: "DeployCandidate" = frappe.get_cached_doc("Deploy Candidate", candidate)
	app_sources = frappe.db.get_all(
		"App Source",
		{"name": ("IN", [app.source for app in deploy_candidate.apps])},
		["name", "branch", "repository", "repository_owner", "repository_url"],
	)
	sources = {
		item["name"]: {
			"branch": item["branch"],
			"repository_url": item["repository_url"],
			"repository": item["repository"],
			"repository_owner": item["repository_owner"],
		}
		for item in app_sources
	}

	return [
		{
			"name": app.app,
			"hash": app.hash[:7],
			"branch": sources.get(app.source).get("branch"),
			"repository": sources.get(app.source).get("repository"),
			"repository_owner": sources.get(app.source).get("repository_owner"),
			"repository_url": sources.get(app.source).get("repository_url"),
		}
		for app in deploy_candidate.apps
	]


@frappe.whitelist()
@protected("Release Group")
def redeploy(name: str, dc_name: str) -> str:
	response = redeploy_candidate(dc_name)

	if response["error"]:
		frappe.throw("Unable to redeploy this build!", frappe.ValidationError)

	return response["message"]


@frappe.whitelist(allow_guest=True)
def confirm_bench_transfer(key: str):
	from frappe import _

	if frappe.session.user == "Guest":
		return frappe.respond_as_web_page(
			_("Not Permitted"),
			_("You need to be logged in to confirm the bench group transfer."),
			http_status_code=403,
			indicator_color="red",
			primary_action="/dashboard/login",
			primary_label=_("Login"),
		)

	if not isinstance(key, str):
		return frappe.respond_as_web_page(
			_("Not Permitted"),
			_("The link you are using is invalid."),
			http_status_code=403,
			indicator_color="red",
		)

	if team_change := frappe.db.get_value("Team Change", {"key": key}):
		team_change = frappe.get_doc("Team Change", team_change)
		to_team = team_change.to_team
		if not frappe.db.get_value(
			"Team Member", {"user": frappe.session.user, "parent": to_team, "parenttype": "Team"}
		):
			return frappe.respond_as_web_page(
				_("Not Permitted"),
				_("You are not a member of the team to which the site is being transferred."),
				http_status_code=403,
				indicator_color="red",
			)

		team_change.transfer_completed = True
		team_change.save()
		frappe.db.commit()

		frappe.response.type = "redirect"
		frappe.response.location = f"/dashboard/groups/{team_change.document_name}"
		return None

	return frappe.respond_as_web_page(
		_("Not Permitted"),
		_("The link you are using is invalid or expired."),
		http_status_code=403,
		indicator_color="red",
	)


@frappe.whitelist()
def search_releases(
	app: str,
	source: str,
	fields: list,
	query: str | None = None,
	limit: int = 10,
	current_release: str | None = None,
):
	if not query:
		return []

	DocType = frappe.qb.DocType("App Release")
	q = (
		frappe.qb.from_(DocType)
		.select(*fields)
		.where(DocType.hash.like(f"%{query.strip()}%") | DocType.message.like(f"%{query.strip()}%"))
	)

	if current_release:
		current_release_creation = frappe.get_value("App Release", current_release, "creation")
		# downgrading apps is not supported
		q = q.where(DocType.creation > current_release_creation)

	q = (
		q.where((DocType.public == 1) & (DocType.status == "Approved"))
		.where((DocType.app == app) & (DocType.source == source))
		.orderby(DocType.timestamp, order=frappe.qb.desc)
		.limit(limit)
	)

	return q.run(as_dict=1)
