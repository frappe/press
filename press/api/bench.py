# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import frappe

import json
from typing import List, Dict
from frappe.utils import comma_and
from collections import OrderedDict
from press.api.site import protected
from press.api.github import branches
from frappe.core.utils import find, find_all
from press.press.doctype.agent_job.agent_job import job_detail
from press.press.doctype.app_source.app_source import AppSource
from press.utils import get_current_team, get_last_doc, unique, get_app_tag
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)


@frappe.whitelist()
def new(bench):
	team = get_current_team(get_doc=True)
	if not team.enabled:
		frappe.throw("You cannot create a new bench because your account is disabled")

	if exists(bench["title"]):
		frappe.throw("A bench exists with the same name")

	apps = [{"app": app["name"], "source": app["source"]} for app in bench["apps"]]
	group = new_release_group(
		bench["title"], bench["version"], apps, team.name, bench["cluster"]
	)
	return group.name


@frappe.whitelist()
@protected("Release Group")
def get(name):
	group = frappe.get_doc("Release Group", name)
	active_benches = frappe.get_all(
		"Bench", {"group": name, "status": "Active"}, limit=1, order_by="creation desc"
	)
	return {
		"name": group.name,
		"title": group.title,
		"version": group.version,
		"status": "Active" if active_benches else "Awaiting Deploy",
		"last_updated": group.modified,
		"creation": group.creation,
	}


@frappe.whitelist()
def all():
	groups = frappe.get_list(
		"Release Group",
		fields=["name", "title", "creation", "version"],
		filters={"enabled": True, "team": get_current_team()},
		order_by="creation desc",
	)

	for group in groups:
		most_recent_candidate = frappe.get_all(
			"Deploy Candidate",
			["status"],
			{"group": group.name},
			limit=1,
			order_by="creation desc",
		)[0]
		active_benches = frappe.get_all(
			"Bench", {"group": group.name, "status": "Active"}, limit=1, order_by="creation desc"
		)
		group.update_available = most_recent_candidate.status == "Draft"
		group.status = "Active" if active_benches else "Awaiting Deploy"
	return groups


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

	cluster_names = unique(
		frappe.db.get_all("Server", filters={"status": "Active"}, pluck="cluster")
	)
	clusters = frappe.db.get_all(
		"Cluster",
		filters={"name": ("in", cluster_names), "public": True},
		fields=["name", "title", "image"],
	)
	options = {"versions": versions, "clusters": clusters}
	return options


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
	app_source.create_release()


@frappe.whitelist()
@protected("Release Group")
def add_app(name, source, app):
	release_group = frappe.get_doc("Release Group", name)
	release_group.add_app(frappe._dict(name=source, app=app))


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
	deployed_versions = frappe.db.get_all(
		"Bench",
		fields=["name", "status"],
		filters={"group": name, "status": ("!=", "Archived")},
		order_by="creation desc",
	)
	for version in deployed_versions:
		version.sites = frappe.db.get_all(
			"Site",
			{"status": ("!=", "Archived"), "group": name, "bench": version.name},
			["name", "status", "creation"],
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
					["branch", "repository", "repository_owner", "repository_url"],
					as_dict=1,
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

	team = get_current_team()
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)

	if rg.team != team:
		frappe.throw(
			"Bench can only be deployed by the bench owner", exc=frappe.PermissionError
		)

	# Throw if a deploy is already in progress
	last_deploy_candidate = get_last_doc("Deploy Candidate", {"group": name})

	if last_deploy_candidate and last_deploy_candidate.status == "Running":
		frappe.throw("A deploy for this bench is already in progress")

	candidate = rg.create_deploy_candidate(apps_to_ignore)
	candidate.build_and_deploy()

	return candidate.name


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
def job(name, job):
	job = frappe.get_doc("Agent Job", job)
	job = job.as_dict()
	job.steps = frappe.get_all(
		"Agent Job Step",
		filters={"agent_job": job.name},
		fields=["step_name", "status", "start", "end", "duration", "output"],
		order_by="creation",
	)
	return job


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

	if marketplace_app and (not belongs_to_current_team(marketplace_app[0])):
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
def search_list():
	groups = frappe.get_list(
		"Release Group",
		fields=["name", "title"],
		filters={"enabled": True, "team": get_current_team()},
		order_by="creation desc",
	)

	return groups
	

@frappe.whitelist()
def archive(name, title):
	benches = frappe.get_list("Bench", filters={"group": name, "status": "Active"})

	for bench in benches:
		frappe.get_doc("Bench", bench.name).archive()

	group = frappe.get_doc("Release Group", name)
	group.title = f"{title}.archived"
	group.enabled = 0
	group.save()
