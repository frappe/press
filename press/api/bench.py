# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

import frappe

from typing import List, Dict
from collections import OrderedDict
from press.api.site import protected
from press.api.github import branches
from frappe.core.utils import find, find_all
from press.press.doctype.agent_job.agent_job import job_detail
from press.utils import get_current_team, get_last_doc, unique
from press.press.doctype.app_source.app_source import AppSource
from press.press.doctype.release_group.release_group import (
	ReleaseGroup,
	new_release_group,
)
from press.press.doctype.deploy_candidate.deploy_candidate import DeployCandidate


@frappe.whitelist()
def new(bench):
	team = get_current_team()
	if exists(bench["title"]):
		frappe.throw("A bench exists with the same name")

	apps = [{"app": app["name"], "source": app["source"]} for app in bench["apps"]]
	group = new_release_group(
		bench["title"], bench["version"], apps, team, bench["cluster"]
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
def add_app(name, source, app):
	release_group = frappe.get_doc("Release Group", name)
	release_group.add_app(frappe._dict(name=source, app=app))


@frappe.whitelist()
@protected("Release Group")
def remove_app(name, app):
	release_group = frappe.get_doc("Release Group", name)
	for app in release_group.apps:
		if app.app == app:
			release_group.remove(app)
			break
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
			["name", "status"],
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
		["name", "creation", "status", "`tabDeploy Candidate App`.app"],
		{"group": name, "status": ("!=", "Draft")},
		order_by="creation desc",
		start=start,
		limit=10,
	)
	candidates = OrderedDict()
	for d in result:
		candidates.setdefault(d.name, {})
		candidates[d.name].update(d)
		candidates[d.name].setdefault("apps", [])
		candidates[d.name]["apps"].append(d.app)

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
	out = frappe._dict(update_available=False)

	last_deployed_bench = get_last_doc("Bench", {"group": name, "status": "Active"})
	out.apps = get_app_updates(
		last_deployed_bench.apps if last_deployed_bench else [], name
	)
	out.update_available = any([app["update_available"] for app in out.apps])

	return out


def get_app_updates(current_apps, rg_name: str):
	rg: ReleaseGroup = frappe.get_doc("Release Group", rg_name)
	next_apps = get_next_apps(rg, current_apps)

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


def get_next_apps(rg: ReleaseGroup, current_apps):
	marketplace_app_sources = rg.get_marketplace_app_sources()
	current_team = get_current_team()
	only_approved_for_sources = [
		source
		for source in marketplace_app_sources
		if frappe.db.get_value("App Source", source, "team") != current_team
	]

	next_apps = []
	for app in rg.apps:
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


@frappe.whitelist()
@protected("Release Group")
def deploy(name, apps_to_ignore=[]):
	team = get_current_team()
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)

	if rg.team != team:
		frappe.throw(
			"Bench can only be deployed by the bench owner", exc=frappe.PermissionError
		)

	# Throw if a deploy is already in progress
	last_deploy_candidate = get_last_doc("Deploy Candidate", {"group": name})

	if last_deploy_candidate.status == "Running":
		frappe.throw("A deploy for this bench is already in progress")

	candidate = create_deploy_candidate(name, apps_to_ignore)
	candidate.build_and_deploy()

	return candidate.name


@frappe.whitelist()
@protected("Release Group")
def create_deploy_candidate(name, apps_to_ignore=[]):
	rg: ReleaseGroup = frappe.get_doc("Release Group", name)

	# Get the deploy information for apps
	# that have updates available
	apps_deploy_info = deploy_information(name).apps

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
		a for a in rg.apps if not find(app_updates, lambda x: x["app"] == a.app)
	]
	last_deployed_bench = get_last_doc("Bench", {"group": name, "status": "Active"})

	if last_deployed_bench:
		for app in untouched_apps:
			update = find(last_deployed_bench.apps, lambda x: x.app == app.app)
			apps.append(
				{
					"release": update.release,
					"source": update.source,
					"app": update.app,
					"hash": update.hash,
				}
			)

	dependencies = [
		{"dependency": d.dependency, "version": d.version} for d in rg.dependencies
	]

	# Create and deploy the DC
	candidate: DeployCandidate = frappe.get_doc(
		{
			"doctype": "Deploy Candidate",
			"group": rg.name,
			"apps": apps,
			"dependencies": dependencies,
		}
	).insert()

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


def get_app_tag(repository, repository_owner, hash):
	return frappe.db.get_value(
		"App Tag",
		{"repository": repository, "repository_owner": repository_owner, "hash": hash},
		"tag",
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
