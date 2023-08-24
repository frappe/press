# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import json
from collections import OrderedDict
from press.press.doctype.team.team import get_child_team_members
from typing import Dict, List

import frappe
from frappe.core.utils import find, find_all
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import comma_and, flt

from press.api.site import protected
from press.api.github import branches
from press.press.doctype.cluster.cluster import Cluster
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)
from press.utils import (
	get_app_tag,
	get_current_team,
	unique,
	get_client_blacklisted_keys,
)


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
	teams = [team] + child_teams

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
		group_names = frappe.get_all(
			"Bench", {"status": "Active"}, pluck="group", distinct=True
		)
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
	return frappe.get_all(
		"Press Tag", {"team": team, "doctype_name": "Release Group"}, pluck="tag"
	)


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
	return bool(frappe.db.exists("Release Group", {"title": title, "team": team}))


@frappe.whitelist()
def options(only_by_current_team=False):
	or_conditions = ""
	# Also, include other public sources
	if not only_by_current_team:
		or_conditions = "OR source.public = 1"

	team = get_current_team()
	rows = frappe.db.sql(
		f"""
	SELECT
		version.name as version,
		version.status as status,
		source.name as source, source.app, source.repository_url, source.repository, source.repository_owner, source.branch,
		source.app_title as title, source.frappe
	FROM
		`tabApp Source Version` AS source_version
	LEFT JOIN
		`tabApp Source` AS source
	ON
		source.name = source_version.parent
	LEFT JOIN
		`tabFrappe Version` AS version
	ON
		source_version.version = version.name
	WHERE
		version.public = 1 AND
		(source.team = %(team)s {or_conditions})
	ORDER BY source.creation
	""",
		{"team": team},
		as_dict=True,
	)

	version_list = unique(rows, lambda x: x.version)
	versions = []
	for d in version_list:
		version_dict = {"name": d.version, "status": d.status}
		version_rows = find_all(rows, lambda x: x.version == d.version)
		app_list = frappe.utils.unique([row.app for row in version_rows])
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

	options = {"versions": versions, "clusters": clusters}
	return options


@frappe.whitelist()
@protected("Release Group")
def bench_config(release_group_name):
	rg = frappe.get_doc("Release Group", release_group_name)

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

	return common_site_config + bench_config


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
		if c.type == "Number":
			c.value = flt(c.value)
		elif c.type == "Boolean":
			c.value = bool(c.value)
		elif c.type == "JSON":
			c.value = frappe.parse_json(c.value)

		if c.key in bench_config_keys:
			sanitized_bench_config.append(c)
		else:
			sanitized_common_site_config.append(c)

	rg = frappe.get_doc("Release Group", name)
	rg.update_config_in_release_group(sanitized_common_site_config, sanitized_bench_config)
	return list(filter(lambda x: not x.internal, rg.common_site_config_table))


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

	for app in group.apps:
		source = frappe.get_doc("App Source", app.source)
		app = frappe.get_doc("App", app.app)
		update_available = updates["update_available"] and find(
			updates.apps, lambda x: x["app"] == app.name and x["update_available"]
		)
		apps.append(
			{
				"name": app.name,
				"frappe": app.frappe,
				"title": app.title,
				"branch": source.branch,
				"repository_url": source.repository_url,
				"repository": source.repository,
				"repository_owner": source.repository_owner,
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
def fetch_latest_app_update(name, app):
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	app_source = rg.get_app_source(app)
	app_source.create_release(force=True)


@frappe.whitelist()
@protected("Release Group")
def add_app(name, source, app):
	add_apps(name, [{"app": app, "source": source}])


@frappe.whitelist()
@protected("Release Group")
def add_apps(name, apps):
	release_group = frappe.get_doc("Release Group", name)
	for app in apps:
		app_name, source = app.values()
		release_group.add_app(frappe._dict(name=source, app=app_name))


@frappe.whitelist()
@protected("Release Group")
def remove_app(name, app):
	release_group: ReleaseGroup = frappe.get_doc("Release Group", name)

	# Sites on this release group
	sites = frappe.get_all(
		"Site", filters={"group": name, "status": ("!=", "Archived")}, pluck="name"
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

	app_doc_to_remove = find(release_group.apps, lambda x: x.app == app)
	if app_doc_to_remove:
		release_group.remove(app_doc_to_remove)

	release_group.save()


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

	for version in deployed_versions:
		version.sites = frappe.db.get_all(
			"Site",
			{
				"status": ("not in", ("Archived", "Suspended")),
				"group": name,
				"bench": version.name,
				"is_standby": 0,
			},
			["name", "status", "cluster", "creation"],
		)
		for site in version.sites:
			site.version = rg_version
			site.server_region_info = frappe.db.get_value(
				"Cluster", site.cluster, ["title", "image"], as_dict=True
			)
			site_plan_name = frappe.get_value("Site", site.name, "plan")
			site.plan = frappe.get_doc("Plan", site_plan_name) if site_plan_name else None
			site.tags = frappe.get_all(
				"Resource Tag",
				{"parent": site.name},
				pluck="tag_name",
			)

		version.apps = frappe.db.get_all(
			"Bench App",
			{"parent": version.name},
			["name", "app", "hash", "source"],
			order_by="idx",
		)
		for app in version.apps:
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

		version.deployed_on = frappe.db.get_value(
			"Agent Job",
			{"bench": version.name, "job_type": "New Bench", "status": "Success"},
			"end",
		)

	return deployed_versions


@frappe.whitelist()
@protected("Release Group")
def candidates(name, start=0):
	result = frappe.get_all(
		"Deploy Candidate",
		["name", "creation", "status"],
		{"group": name, "status": ("!=", "Draft")},
		order_by="creation desc",
		start=start,
		limit=10,
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
	candidate = frappe.get_doc("Deploy Candidate", name)
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
			)[0]
			jobs.append(job)

	return {
		"name": candidate.name,
		"status": candidate.status,
		"creation": candidate.creation,
		"deployed": False,
		"build_steps": candidate.build_steps,
		"build_start": candidate.build_start,
		"build_end": candidate.build_end,
		"build_duration": candidate.build_duration,
		"apps": candidate.apps,
		"jobs": jobs,
	}


@frappe.whitelist()
@protected("Release Group")
def deploy_information(name):
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	return rg.deploy_information()


@frappe.whitelist()
@protected("Release Group")
def deploy(name, apps_to_ignore=[]):
	if isinstance(apps_to_ignore, str):
		apps_to_ignore = json.loads(apps_to_ignore)

	team = get_current_team(True)
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)

	if rg.team != team.name:
		frappe.throw(
			"Bench can only be deployed by the bench owner", exc=frappe.PermissionError
		)

	if rg.deploy_in_progress:
		frappe.throw("A deploy for this bench is already in progress")

	candidate = rg.create_deploy_candidate(apps_to_ignore)
	candidate.deploy_to_production()

	return candidate.name


@frappe.whitelist()
@protected("Release Group")
def deploy_and_update(name, apps_to_ignore=[], sites=[]):
	if isinstance(apps_to_ignore, str):
		apps_to_ignore = json.loads(apps_to_ignore)

	team = get_current_team(True)
	rg_team = frappe.db.get_value("Release Group", name, "team")

	if rg_team != team.name:
		frappe.throw(
			"Bench can only be deployed by the bench owner", exc=frappe.PermissionError
		)
	bench_update = frappe.get_doc(
		{
			"doctype": "Bench Update",
			"group": name,
			"sites": [
				{
					"site": site["name"],
					"server": site["server"],
					"skip_failing_patches": site["skip_failing_patches"],
					"skip_backups": site["skip_backups"],
					"source_candidate": frappe.get_value("Bench", site["bench"], "candidate"),
				}
				for site in sites
			],
			"status": "Pending",
		}
	).insert(ignore_permissions=True)
	bench_update.deploy(apps_to_ignore=apps_to_ignore)


@frappe.whitelist()
@protected("Release Group")
def create_deploy_candidate(name, apps_to_ignore=[]):
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	candidate = rg.create_deploy_candidate(apps_to_ignore)

	return candidate


@frappe.whitelist()
@protected("Release Group")
def jobs(name, start=0):
	benches = frappe.get_all("Bench", {"group": name}, pluck="name")
	if benches:
		jobs = frappe.get_all(
			"Agent Job",
			fields=["name", "job_type", "creation", "status", "start", "end", "duration"],
			filters={"bench": ("in", benches)},
			start=start,
			limit=10,
			ignore_ifnull=True,
		)
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
def branch_list(name: str, app: str) -> List[Dict]:
	"""Return a list of git branches available for the `app`"""
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)
	app_source = rg.get_app_source(app)

	installation_id = app_source.github_installation_id
	repo_owner = app_source.repository_owner
	repo_name = app_source.repository

	marketplace_app = frappe.get_all(
		"Marketplace App", filters={"app": app}, pluck="name", limit=1
	)

	if (
		marketplace_app
		and app_source.public
		and (not belongs_to_current_team(marketplace_app[0]))
	):
		return get_branches_for_marketplace_app(app, marketplace_app[0], app_source)

	return branches(installation_id, repo_owner, repo_name)


def get_branches_for_marketplace_app(
	app: str, marketplace_app: str, app_source: AppSource
) -> List[Dict]:
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
	clusters = frappe.get_all(
		"Cluster", fields=["name", "title", "image"], filters={"name": ("in", cluster_names)}
	)
	return clusters


@frappe.whitelist()
@protected("Release Group")
def available_regions(name):
	rg = frappe.get_doc("Release Group", name)
	cluster_names = rg.get_clusters()
	return Cluster.get_all_for_new_bench({"name": ("not in", cluster_names)})


@frappe.whitelist()
@protected("Release Group")
def add_region(name, region):
	rg = frappe.get_doc("Release Group", name)
	if len(rg.get_clusters()) >= 2:
		frappe.throw("More than 2 regions for bench not allowed")
	rg.add_cluster(region)


@frappe.whitelist()
@protected("Release Group")
def archive(name):
	benches = frappe.get_all(
		"Bench", filters={"group": name, "status": "Active"}, pluck="name"
	)

	for bench in benches:
		frappe.get_doc("Bench", bench).archive()

	group = frappe.get_doc("Release Group", name)
	new_name = f"{group.title}.archived"
	group.title = append_number_if_name_exists(
		"Release Group", new_name, "title", separator="."
	)
	group.enabled = 0
	group.save()


@frappe.whitelist()
@protected("Release Group")
def restart(bench):
	frappe.get_doc("Bench", bench).restart()


@frappe.whitelist()
@protected("Release Group")
def update(bench):
	frappe.get_doc("Bench", bench).update_all_sites()


@frappe.whitelist()
@protected("Release Group")
def update_all_sites(bench_name):
	benches = frappe.get_all("Bench", {"group": bench_name, "status": "Active"})
	for bench in benches:
		frappe.get_cached_doc("Bench", bench).update_all_sites()


@frappe.whitelist()
@protected("Bench")
def logs(name, bench):
	if frappe.db.get_value("Bench", bench, "group") == name:
		return frappe.get_doc("Bench", bench).server_logs


@frappe.whitelist()
@protected("Bench")
def log(name, bench, log):
	if frappe.db.get_value("Bench", bench, "group") == name:
		return frappe.get_doc("Bench", bench).get_server_log(log)


@frappe.whitelist()
@protected("Release Group")
def certificate(name):
	certificates = frappe.get_all(
		"SSH Certificate",
		{
			"user": frappe.session.user,
			"valid_until": [">", frappe.utils.now()],
			"group": name,
		},
		pluck="name",
		limit=1,
	)
	if certificates:
		return frappe.get_doc("SSH Certificate", certificates[0])


@frappe.whitelist()
@protected("Release Group")
def generate_certificate(name):
	user_ssh_key = frappe.get_all(
		"User SSH Key", {"user": frappe.session.user, "is_default": True}, pluck="name"
	)[0]
	return frappe.get_doc(
		{
			"doctype": "SSH Certificate",
			"certificate_type": "User",
			"group": name,
			"user": frappe.session.user,
			"user_ssh_key": user_ssh_key,
			"validity": "6h",
		}
	).insert()


@frappe.whitelist()
@protected("Release Group")
def get_title_and_creation(name):
	result = frappe.db.get_value(
		"Release Group", name, ["title", "creation"], as_dict=True
	)
	server = frappe.get_all(
		"Release Group Server", {"parent": name}, pluck="server", order_by="idx asc", limit=1
	)[0]
	result["team"] = frappe.db.get_value("Server", server, "team")
	return result


@frappe.whitelist()
@protected("Release Group")
def rename(name, title):
	return frappe.db.set_value("Release Group", name, "title", title)
