# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team
from press.api.site import protected
from frappe.core.utils import find
from press.press.doctype.app.app import new_app


@frappe.whitelist()
def new(app):
	name = app["name"]
	team = get_current_team()

	if frappe.db.exists("App", name):
		app_doc = frappe.get_doc("App", name)
	else:
		app_doc = new_app(name, app["title"])
	group = frappe.get_doc("Release Group", app["group"])

	source = app_doc.add_source(
		group.version,
		app["repository_url"],
		app["branch"],
		team,
		app["github_installation_id"],
	)

	group.add_app(source)
	return group.name


@frappe.whitelist()
@protected("App")
def get(name):
	app = frappe.get_doc("App", name)
	team = get_current_team()
	sources = frappe.get_all(
		"App Source", filters={"app": name}, or_filters={"team": team, "public": True},
	)
	versions = frappe.get_all(
		"App Source Version",
		fields=["version as name"],
		filters={"parent": ("in", [source.name for source in sources])},
		group_by="version",
	)

	return {
		"name": app.name,
		"title": app.title,
		"installations": 124,
		"versions": versions,
		"modified": app.modified,
		"creation": app.creation,
	}


@frappe.whitelist()
def sources(name):
	team = get_current_team()
	rows = frappe.db.sql(
		"""
	SELECT
		source.name , source.repository_url, source.repository, source.repository_owner, source.branch,
		version.number as version
	FROM
		`tabApp Source` AS source
	LEFT JOIN
		`tabApp Source Version` AS source_version
	ON
		source_version.parent = source.name
	LEFT JOIN
		`tabFrappe Version` AS version
	ON
		source_version.version = version.name
	WHERE
		(source.team = %(team)s OR source.public = 1) AND
		source.app = %(app)s
	ORDER BY version.creation, source.creation
	""",
		{"team": team, "app": name},
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
@protected("App")
def releases(name):
	releases = frappe.get_all(
		"App Release",
		filters={"app": name},
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
		source.app as name, app.title, app.modified
	FROM
		`tabApp Source` AS source
	LEFT JOIN
		`tabApp` AS app
	ON
		source.app = app.name
	WHERE
		(source.team = %(team)s OR source.public = 1)
	GROUP BY source.app
	ORDER BY source.creation DESC
	""",
		{"team": team},
		as_dict=True,
	)
	return apps


@frappe.whitelist()
@protected("App")
def deploy(name):
	release = frappe.get_all(
		"App Release",
		{"app": name, "deployable": False, "status": "Approved"},
		order_by="creation desc",
		limit=1,
	)[0]
	release_doc = frappe.get_doc("App Release", release)
	release_doc.deploy()
