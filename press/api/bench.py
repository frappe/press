# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team
from press.api.site import protected
from frappe.core.utils import find_all
from press.press.doctype.release_group.release_group import new_release_group


@frappe.whitelist()
def new(bench):
	team = get_current_team()
	apps = [
		{"app": app["name"], "source": app["source"]} for app in bench["apps"]
	]
	group = new_release_group(bench["title"], bench["version"], apps, team)
	return group.name


@frappe.whitelist()
@protected("Release Group")
def get(name):
	group = frappe.get_doc("Release Group", name)
	return {
		"name": group.name,
		"title": group.title,
		"version": group.version,
		"status": "Active",
		"update_available": True,
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
		group.status = "Active"
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
		source.name as source, source.app, source.repository_url, source.repository, source.repository_owner, source.branch,
		app.title, app.frappe
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
	LEFT JOIN
		`tabApp` AS app
	ON
		source.app = app.name
	WHERE
		version.public = 1 AND
		(source.team = %(team)s OR source.public = 1)
	ORDER BY app.creation, source.creation
	""",
		{"team": team},
		as_dict=True,
	)

	version_list = frappe.utils.unique([row.version for row in rows])
	versions = []
	for version in version_list:
		version_dict = {"name": version}
		version_rows = find_all(rows, lambda x: x.version == version)
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
	for app in group.apps:
		source = frappe.get_doc("App Source", app.source)
		app = frappe.get_doc("App", app.app)

		apps.append(
			{
				"name": app.name,
				"frappe": app.frappe,
				"title": app.title,
				"branch": source.branch,
				"repository_url": source.repository_url,
				"repository": source.repository,
				"repository_owner": source.repository_owner,
			}
		)
	return apps


@frappe.whitelist()
@protected("Release Group")
def candidates(name):
	candidates = frappe.get_all(
		"Deploy Candidate",
		["name", "creation", "status"],
		{"group": name, "status": ("!=", "Draft")},
		order_by="creation desc",
		limit=20,
	)
	return candidates


@frappe.whitelist()
def candidate(name):
	candidate = frappe.get_doc("Deploy Candidate", name)
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
	}


@frappe.whitelist()
def deploy(name):
	candidate = frappe.get_all(
		"Deploy Candidate", {"group": name}, limit=1, order_by="creation desc"
	)[0]
	candidate = frappe.get_doc("Deploy Candidate", candidate.name)
	candidate.build_and_deploy()
	return candidate.name
