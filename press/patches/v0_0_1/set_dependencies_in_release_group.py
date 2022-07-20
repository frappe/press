# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "release_group_dependency")
	frappe.reload_doc("press", "doctype", "release_group")

	for name in frappe.db.get_all("Release Group", pluck="name"):
		release_group = frappe.get_doc("Release Group", name)
		release_group.extend(
			"dependencies",
			[
				{"dependency": "NVM_VERSION", "version": "0.36.0"},
				{"dependency": "NODE_VERSION", "version": "12.19.0"},
				{"dependency": "PYTHON_VERSION", "version": "3.7"},
				{"dependency": "WKHTMLTOPDF_VERSION", "version": "0.12.5"},
			],
		)
		release_group.db_update_all()
