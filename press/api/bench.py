# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from collections import OrderedDict
import frappe
from press.utils import get_current_team, get_last_doc, unique
from press.api.site import protected
from frappe.core.utils import find, find_all
from press.press.doctype.release_group.release_group import new_release_group
from press.press.doctype.agent_job.agent_job import job_detail


@frappe.whitelist()
def new(bench):
	team = get_current_team()
	if exists(bench["title"]):
		frappe.throw("A bench exists with the same name")

	apps = [{"app": app["name"], "source": app["source"]} for app in bench["apps"]]
	group = new_release_group(bench["title"], bench["version"], apps, team)
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
def options():
	team = get_current_team()
	rows = frappe.db.sql(
		"""
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
		(source.team = %(team)s OR source.public = 1)
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
	options = {
		"versions": versions,
	}
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
			"Site", {"status": ("!=", "Archived"), "group": name, "bench": version.name}
		)
		version.apps = frappe.db.get_all(
			"Bench App", {"parent": version.name}, ["name", "app", "hash", "source"]
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
	last_deploy_candidate = get_last_doc(
		"Deploy Candidate", {"group": name, "status": "Draft"}
	)
	if not last_deploy_candidate:
		return out

	last_deployed_bench = get_last_doc("Bench", {"group": name, "status": "Active"})
	out.apps = get_updates_between_current_and_next_apps(
		last_deployed_bench.apps if last_deployed_bench else [], last_deploy_candidate.apps
	)
	out.update_available = any([app["update_available"] for app in out.apps])
	return out


def get_updates_between_current_and_next_apps(current_apps, next_apps):
	apps = []
	for app in next_apps:
		bench_app = find(current_apps, lambda x: x.app == app.app)
		current_hash = bench_app.hash if bench_app else None
		source = frappe.get_doc("App Source", app.source)
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
				"repository": source.repository,
				"repository_owner": source.repository_owner,
				"repository_url": source.repository_url,
				"branch": source.branch,
				"current_hash": current_hash,
				"current_tag": current_tag,
				"next_hash": next_hash,
				"next_tag": get_app_tag(source.repository, source.repository_owner, next_hash),
				"update_available": not current_hash or current_hash != next_hash,
			}
		)
	return apps


@frappe.whitelist()
@protected("Release Group")
def deploy(name):
	candidate = frappe.get_all(
		"Deploy Candidate",
		["name", "status"],
		{"group": name},
		limit=1,
		order_by="creation desc",
	)[0]
	if candidate.status != "Draft":
		return
	candidate = frappe.get_doc("Deploy Candidate", candidate.name)
	candidate.build_and_deploy()
	return candidate.name


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
def change_branch(name, app, to_branch):
	'''Switch to `to_branch` for `app` in release group `name`'''
	rg = frappe.get_doc("Release Group", name)
	rg.change_app_branch(app, to_branch)
