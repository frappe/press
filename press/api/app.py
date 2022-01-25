# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import json
import frappe
from press.utils import get_current_team
from press.press.doctype.app.app import new_app


@frappe.whitelist()
def new(app):
	if isinstance(app, str):
		app = json.loads(app)

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
