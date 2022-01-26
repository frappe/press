# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.utils.fixtures import sync_fixtures


def execute():
	frappe.reload_doc("press", "doctype", "app")
	frappe.reload_doc("press", "doctype", "app_source")
	frappe.reload_doc("press", "doctype", "frappe_version")
	sync_fixtures("press")
	frappe.reload_doc("press", "doctype", "app_source_version")
	frappe.reload_doc("press", "doctype", "app_release")
	frappe.reload_doc("press", "doctype", "app_release_difference")
	frappe.reload_doc("press", "doctype", "release_group_app")
	frappe.reload_doc("press", "doctype", "bench_app")
	frappe.reload_doc("press", "doctype", "deploy_candidate_app")
	distinct_apps = frappe.get_all("App", ["title", "scrubbed"], group_by="scrubbed")

	for distinct_app in distinct_apps:
		apps = frappe.get_all(
			"App", "*", {"scrubbed": distinct_app.scrubbed}, order_by="enabled desc"
		)
		for app in apps:
			versions = set(frappe.get_all("Release Group", {"app": app.name}, pluck="version"))
			if not versions:
				groups = frappe.get_all("Bench", {"app": app.name}, pluck="group")
				versions = set(
					frappe.get_all("Release Group", {"name": ("in", groups)}, pluck="version")
				)
			if not versions:
				continue
			source = {
				"doctype": "App Source",
				"app": app.name,
				"app_title": app.title,
				"frappe": app.frappe,
				"enabled": app.enabled,
				"repository_url": app.url,
				"repository": app.repo,
				"repository_owner": app.repo_owner,
				"branch": app.branch,
				"github_installation_id": app.installation,
				"public": app.public,
				"team": app.team,
				"versions": [{"version": version} for version in versions],
			}
			source = frappe.get_doc(source)
			source.name = "TEMP-SOURCE"
			source.set_parent_in_children()
			source.db_insert()

			for child in source.get_all_children():
				child.db_insert()

			frappe.db.set_value("App Release", {"app": app.name}, "source", source.name)
			frappe.db.set_value("Bench App", {"app": app.name}, "source", source.name)
			frappe.db.set_value("Deploy Candidate App", {"app": app.name}, "source", source.name)
			frappe.db.set_value("Release Group App", {"app": app.name}, "source", source.name)
			frappe.db.set_value("Release Group App", {"app": app.name}, "title", app.title)

			existing = frappe.db.exists("App", app.scrubbed, cache=False)
			if existing and existing == app.scrubbed:
				frappe.rename_doc("App", app.name, app.scrubbed, merge=True)
			else:
				frappe.rename_doc("App", app.name, app.scrubbed)

			old_source_name = source.name
			source.reload()
			source.autoname()
			frappe.rename_doc("App Source", old_source_name, source.name)


def delete():
	frappe.db.set_value("App Release", {"cloned": False}, "source", None)
	for difference in frappe.get_all("App Release Difference"):
		frappe.delete_doc("App Release Difference", difference.name)
	for source in frappe.get_all("App Source"):
		frappe.delete_doc("App Source", source.name)
	frappe.db.delete(
		"Patch Log", {"patch": "press.patches.v0_0_1.create_app_source_from_app"}
	)
