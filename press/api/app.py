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
	app_doc = frappe.get_doc(
		{
			"doctype": "Frappe App",
			"name": f"{app['repo_owner']}/{app['repo']}",
			"branch": app["branch"],
			"url": app["url"],
			"repo": app["repo"],
			"repo_owner": app["repo_owner"],
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
@protected("Frappe App")
def get(name):
	app = frappe.get_doc("Frappe App", name)
	return {
		"name": app.name,
		"branch": app.branch,
		"repo": app.repo,
		"enable_auto_deploy": app.enable_auto_deploy,
		"scrubbed": app.scrubbed,
		"owner": app.repo_owner,
		"url": app.url,
		"last_updated": app.modified,
		"created": app.creation,
	}


@frappe.whitelist()
@protected("Frappe App")
def deploys(name):
	deploys = frappe.get_all(
		"Bench",
		filters={"status": ("!=", "Archived")},
		fields=["name", "server", "status", "creation", "`group`"],
	)
	return deploys


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
		],
		order_by="creation desc",
	)
	tags = frappe.get_all(
		"App Tag",
		filters={
			"repository": app.repo,
			"repository_owner": app.repo_owner,
			"installation": app.installation,
		},
		fields=["hash", "tag"],
	)
	for tag in tags:
		release = find(releases, lambda x: x.hash == tag.hash)
		if release:
			release.setdefault("tags", []).append(tag.tag)

	return releases


@frappe.whitelist()
def all():
	if frappe.session.data.user_type == "System User":
		filters = {}
	else:
		filters = {"team": get_current_team()}
	apps = frappe.get_list(
		"Frappe App",
		fields=["name", "modified", "url", "branch"],
		filters=filters,
		order_by="creation desc",
	)

	return apps


@frappe.whitelist()
@protected("Frappe App")
def deploy(name, release):
	release = frappe.get_doc("App Release", release)
	deploy = release.deploy()
	return deploy.name
