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
	applications = [
		{"app": app["name"], "source": app["source"]} for app in bench["applications"]
	]
	group = new_release_group(bench["version"], bench["title"], applications, team)
	return group.name


@frappe.whitelist()
@protected("Release Group")
def get(name):
	group = frappe.get_doc("Release Group", name)
	apps = []
	for app in group.apps:
		source = frappe.get_doc("Application Source", app.source)
		application = frappe.get_doc("Application", app.app)

		apps.append(
			{
				"name": application.name,
				"frappe": application.frappe,
				"title": application.title,
				"branch": source.branch,
				"repository_url": source.repository_url,
				"repository": source.repository,
				"repository_owner": source.repository_owner,
			}
		)
	return {
		"name": group.name,
		"title": group.title,
		"version": group.version,
		"status": "Active",
		"apps": apps,
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
		source.name as source, source.application, source.repository_url, source.repository, source.repository_owner, source.branch,
		application.title, application.frappe
	FROM
		`tabFrappe Version` AS version
	LEFT JOIN
		`tabApplication Source` AS source
	ON
		source.version = version.name
	LEFT JOIN
		`tabApplication` AS application
	ON
		source.application = application.name
	WHERE
		version.public = 1 AND
		(source.team = %(team)s OR source.public = 1)
	ORDER BY application.creation, source.creation
	""",
		{"team": team},
		as_dict=True,
	)

	version_list = frappe.utils.unique([row.version for row in rows])
	versions = []
	for version in version_list:
		version_dict = {"name": version}
		version_rows = find_all(rows, lambda x: x.version == version)
		application_list = frappe.utils.unique([row.application for row in version_rows])
		for application in application_list:
			application_rows = find_all(version_rows, lambda x: x.application == application)
			application_dict = {"name": application, "title": application_rows[0].title}
			for source in application_rows:
				source_dict = {
					"name": source.source,
					"repository_url": source.repository_url,
					"branch": source.branch,
					"repository": source.repository,
					"repository_owner": source.repository_owner,
				}
				application_dict.setdefault("sources", []).append(source_dict)
			application_dict["source"] = application_dict["sources"][0]
			version_dict.setdefault("applications", []).append(application_dict)
		versions.append(version_dict)
	options = {
		"versions": versions,
	}
	return options
