# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import json
import frappe
from press.utils import get_current_team
from press.press.doctype.app.app import new_app
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from press.press.doctype.app.app import App
	from press.press.doctype.release_group.release_group import ReleaseGroup


@frappe.whitelist()
def new(app):
	if isinstance(app, str):
		app = json.loads(app)

	name = app["name"]
	team = get_current_team()

	if frappe.db.exists("App", name):
		app_doc: "App" = frappe.get_doc("App", name)
	else:
		app_doc: "App" = new_app(name, app["title"])
	group: "ReleaseGroup" = frappe.get_doc("Release Group", app["group"])

	source = app_doc.add_source(
		group.version,
		app["repository_url"],
		app["branch"],
		team,
		app["github_installation_id"] if "github_installation_id" in app else None,
	)

	group.append_source(source)
	return group.name
