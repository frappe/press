# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team
from press.api.site import protected
from frappe.core.utils import find
from press.press.doctype.application.application import new_application


@frappe.whitelist()
def new(app):
	name = app["name"]
	team = get_current_team()
	if frappe.db.exists("Application", name):
		app_doc = frappe.get_doc("Application", name)
	else:
		app_doc = new_application(name, app["title"])
	for version in app["versions"]:
		app_doc.add_source(
			version, app["repository_url"], app["branch"], team, app["github_installation_id"]
		)
	return app_doc.name


def update_available(name):
	releases = frappe.get_all(
		"Application Release",
		fields=["deployable"],
		filters={"application": name, "status": "Approved"},
		order_by="creation desc",
		limit=1,
	)
	if releases and not releases[0].deployable:
		return True
	return False


def app_status(name):
	status = frappe.get_all(
		"Application Release",
		fields=["status"],
		filters={"application": name},
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
@protected("Application")
def get(name):
	app = frappe.get_doc("Application", name)
	team = get_current_team()
	sources = frappe.get_all(
		"Application Source",
		filters={"application": name},
		or_filters={"team": team, "public": True},
	)
	versions = frappe.get_all(
		"Application Source",
		fields=["version as name"],
		filters={"application": name},
		or_filters={"team": team, "public": True},
		group_by="version",
	)

	return {
		"name": app.name,
		"title": app.title,
		"update_available": True,
		"installations": 124,
		"versions": versions,
		"sources": sources,
		"modified": app.modified,
		"creation": app.creation,
	}


@frappe.whitelist()
@protected("Application")
def deploys(name):
	releases = frappe.get_all(
		"Application Release",
		filters={"application": name, "deployable": True, "status": "Approved"},
		fields=["name", "hash", "creation", "message", "app"],
		order_by="creation desc",
		limit=10,
	)

	group_names = frappe.get_all(
		"Release Group Application", fields=["parent as name"], filters={"app": name}
	)
	groups = {}
	for group in group_names:
		group_doc = frappe.get_doc("Release Group", group.name)
		if not group_doc.enabled:
			continue
		frappe_app = frappe.get_all(
			"Application",
			fields=["name", "scrubbed", "branch"],
			filters={
				"name": ("in", [row.app for row in group_doc.applications]),
				"frappe": True,
			},
		)[0]
		groups[group.name] = frappe_app

	app = frappe.get_doc("Application", name)
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
def sources(name):
	team = get_current_team()
	rows = frappe.db.sql(
		"""
	SELECT
		source.name , source.repository_url, source.repository, source.repository_owner, source.branch,
		version.number as version
	FROM
		`tabApplication Source` AS source
	LEFT JOIN
		`tabFrappe Version` AS version
	ON
		source.version = version.name
	WHERE
		(source.team = %(team)s OR source.public = 1) AND
		source.application = %(application)s
	ORDER BY version.creation, source.creation
	""",
		{"team": team, "application": name},
		as_dict=True,
	)
	sources = []
	for row in rows:
		signature = (row.repository_url, row.branch)
		source = find(sources, lambda x: x["signature"] == signature)
		if not source:
			source = {
				"repository_url": row.repository_url,
				"repository_owner": row.repository_owner,
				"repository": row.repository,
				"branch": row.branch,
				"signature": signature,
				"versions": [],
			}
			sources.append(source)
		source["versions"].append({"name": row.name, "version": row.version})
	return sources


@frappe.whitelist()
@protected("Application")
def releases(name):
	releases = frappe.get_all(
		"Application Release",
		filters={"application": name},
		fields=["name", "hash", "creation", "message", "author"],
		order_by="creation desc",
		limit=10,
	)

	return releases


@frappe.whitelist()
def all():
	team = get_current_team()
	apps = frappe.db.sql(
		"""
	SELECT
		source.application as name, application.title, application.modified
	FROM
		`tabApplication Source` AS source
	LEFT JOIN
		`tabApplication` AS application
	ON
		source.application = application.name
	WHERE
		(source.team = %(team)s OR source.public = 1)
	GROUP BY source.application
	ORDER BY source.creation DESC
	""",
		{"team": team},
		as_dict=True,
	)
	for app in apps:
		app["update_available"] = True
	return apps


@frappe.whitelist()
@protected("Application")
def deploy(name):
	release = frappe.get_all(
		"Application Release",
		{"application": name, "deployable": False, "status": "Approved"},
		order_by="creation desc",
		limit=1,
	)[0]
	release_doc = frappe.get_doc("Application Release", release)
	release_doc.deploy()
