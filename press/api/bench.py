# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from press.utils import get_current_team
from press.api.site import protected
from frappe.core.utils import find_all


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


