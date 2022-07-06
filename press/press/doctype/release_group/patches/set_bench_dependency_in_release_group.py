# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	for name in frappe.db.get_all("Release Group", pluck="name"):
		release_group = frappe.get_doc("Release Group", name)
		release_group.extend(
			"dependencies",
			[
				{"dependency": "BENCH_VERSION", "version": "5.2.1"},
			],
		)
		release_group.db_update_all()
