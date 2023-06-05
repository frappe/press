# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
import os


def execute():
	frappe.reload_doctype("App Release")
	clone_directory = frappe.db.get_single_value("Press Settings", "clone_directory")
	releases = frappe.get_all(
		"App Release",
		{"clone_directory": ("is", "not set")},
		["name", "app", "source", "hash"],
	)
	for release in releases:
		frappe.db.set_value(
			"App Release",
			release.name,
			"clone_directory",
			os.path.join(clone_directory, release.app, release.source, release.hash[:10]),
			update_modified=False,
		)
