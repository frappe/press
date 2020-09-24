# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team
from press.api.site import protected
from frappe.core.utils import find


@frappe.whitelist()
def new(app):
	team = get_current_team()
	repo_owner, repo, branch = app["repo_owner"], app["repo"], app["branch"]
	existing = frappe.db.exists(
		"Frappe App", {"repo_owner": repo_owner, "repo": repo, "branch": branch},
	)
	if existing:
		frappe.throw(
			f"App with repository {repo_owner}/{repo} and branch {branch} already exists."
		)

	app_doc = frappe.get_doc(
		{
			"doctype": "Frappe App",
			"name": app["name"],
			"branch": branch,
			"repo": repo,
			"repo_owner": repo_owner,
			"url": app["url"],
			"scrubbed": app["scrubbed"],
			"installation": app["installation"],
			"team": team,
			"enable_auto_deploy": app["enable_auto_deploy"],
		}
	)
	app_doc.insert()
	for group in app["groups"]:
		release_group = frappe.get_doc("Release Group", group)
		release_group.append("apps", {"app": app_doc.name})
		release_group.save()
	return app_doc.name


@frappe.whitelist()
def exists(name):
	return bool(frappe.db.exists("Frappe App", name))


@frappe.whitelist()
def similar_exists(repo_owner, repo, branch):
	return bool(
		frappe.db.exists(
			"Frappe App", {"repo": repo, "repo_owner": repo_owner, "branch": branch}
		)
	)


def update_available(name):
	releases = frappe.get_all(
		"App Release",
		fields=["deployable"],
		filters={"app": name, "status": "Approved"},
		order_by="creation desc",
		limit=1,
	)
	if releases and not releases[0].deployable:
		return True
	return False


def app_status(name):
	status = frappe.get_all(
		"App Release",
		fields=["status"],
		filters={"app": name},
		order_by="creation desc",
		limit=1,
	)[0].status
	return {
		"Approved": "Active",
		"Pending": "Pending",
		"Awaiting Approval": "Awaiting Approval",
		"Rejected": "Rejected",
	}[status]


@frappe.whitelist()
@protected("Frappe App")
def get(name):
	app = frappe.get_doc("Frappe App", name)
	groups = frappe.get_all(
		"Release Group Frappe App", fields=["parent as name"], filters={"app": app.name}
	)
	enabled_groups = []
	for group in groups:
		group_doc = frappe.get_doc("Release Group", group.name)
		if not group_doc.enabled:
			continue
		frappe_app = frappe.get_all(
			"Frappe App",
			fields=["name", "scrubbed", "branch"],
			filters={"name": ("in", [row.app for row in group_doc.apps]), "frappe": True},
		)[0]
		group["frappe"] = frappe_app
		enabled_groups.append(group)

	return {
		"name": app.name,
		"branch": app.branch,
		"status": app_status(app.name),
		"repo": app.repo,
		"enable_auto_deploy": app.enable_auto_deploy,
		"scrubbed": app.scrubbed,
		"groups": enabled_groups,
		"repo_owner": app.repo_owner,
		"url": app.url,
		"update_available": update_available(app.name),
		"last_updated": app.modified,
		"creation": app.creation,
	}


@frappe.whitelist()
@protected("Frappe App")
def deploys(name):
	releases = frappe.get_all(
		"App Release",
		filters={"app": name, "deployable": True, "status": "Approved"},
		fields=["name", "hash", "creation", "message", "app"],
		order_by="creation desc",
		limit=10,
	)

	group_names = frappe.get_all(
		"Release Group Frappe App", fields=["parent as name"], filters={"app": name}
	)
	groups = {}
	for group in group_names:
		group_doc = frappe.get_doc("Release Group", group.name)
		if not group_doc.enabled:
			continue
		frappe_app = frappe.get_all(
			"Frappe App",
			fields=["name", "scrubbed", "branch"],
			filters={"name": ("in", [row.app for row in group_doc.apps]), "frappe": True},
		)[0]
		groups[group.name] = frappe_app

	app = frappe.get_doc("Frappe App", name)
	tags = frappe.get_all(
		"App Tag",
		filters={"repository": app.repo, "repository_owner": app.repo_owner},
		fields=["hash", "tag"],
	)
	for tag in tags:
		release = find(releases, lambda x: x.hash == tag.hash)
		if release:
			release.setdefault("tags", []).append(tag.tag)

	for release in releases:
		release["groups"] = []
		for group in groups:
			benches = frappe.get_all(
				"Bench",
				{"group": group, "app": release.app, "hash": release.hash},
				["status", "group"],
			)
			statuses = set(bench.status for bench in benches)
			if benches:
				bench = benches[0]
				for status in ("Active", "Installing", "Pending", "Broken", "Archived"):
					if status in statuses:
						bench.status = status
						break
				release["groups"].append(bench)

	return {"groups": groups, "releases": releases}


@frappe.whitelist()
@protected("Frappe App")
def releases(name):
	app = frappe.get_doc("Frappe App", name)
	releases = frappe.get_all(
		"App Release",
		filters={"app": name},
		fields=[
			"name",
			"hash",
			"creation",
			"message",
			"author",
			"status",
			"reason",
			"comments",
			"deployable",
		],
		order_by="creation desc",
		limit=10,
	)
	tags = frappe.get_all(
		"App Tag",
		filters={"repository": app.repo, "repository_owner": app.repo_owner},
		fields=["hash", "tag"],
	)
	for tag in tags:
		release = find(releases, lambda x: x.hash == tag.hash)
		if release:
			release.setdefault("tags", []).append(tag.tag)

	return releases


@frappe.whitelist()
def all():
	filters = {"enabled": True}
	if frappe.session.data.user_type != "System User":
		filters.update({"team": get_current_team()})
	apps = frappe.get_list(
		"Frappe App",
		fields=["name", "modified", "url", "repo_owner", "repo", "branch"],
		filters=filters,
		order_by="creation desc",
	)
	for app in apps:
		app["update_available"] = update_available(app.name)
		app["status"] = app_status(app.name)

	return apps


@frappe.whitelist()
@protected("Frappe App")
def deploy(name):
	release = frappe.get_all(
		"App Release",
		{"app": name, "deployable": False, "status": "Approved"},
		order_by="creation desc",
		limit=1,
	)[0]
	release_doc = frappe.get_doc("App Release", release)
	release_doc.deploy()


@frappe.whitelist(allow_guest=True)
def marketplace_apps():
	# TODO: Caching, Pagination, Filtering, Sorting
	return frappe.get_all(
		"Marketplace App", filters={"status": "Published"}, fields=["*"]
	)
