# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
import frappe


def execute():
	sites = frappe.get_all(
		"Site",
		filters={
			"status": ("!=", "Archived"),
			"is_database_access_enabled": 1,
			"database_access_mode": ["in", ("read_only", "read_write")],
		},
		pluck="name",
	)
	if sites:
		for site_name in sites:
			site = frappe.get_doc("Site", site_name)
			db_user = frappe.get_doc(
				{
					"doctype": "Site Database User",
					"site": site.name,
					"team": site.team,
					"mode": site.database_access_mode,
					"user_created_in_database": True,
					"user_added_in_proxysql": True,
					"username": site.database_access_user,
					"password": site.get_password("database_access_password"),
				}
			)
			db_user.flags.ignore_after_insert_hooks = True
			db_user.insert(ignore_permissions=True)
			frappe.db.set_value("Site Database User", db_user.name, "status", "Active")
