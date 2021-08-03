# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

import frappe


def execute():
	frappe.reload_doctype("App Release")
	app_releases = frappe.get_all(
		"App Release", {"status": ("is", "not set")}, pluck="name"
	)

	for release in app_releases:
		frappe.db.set_value("App Release", release, "status", "Draft")
