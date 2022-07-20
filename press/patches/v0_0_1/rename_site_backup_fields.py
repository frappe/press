# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site_backup")
	frappe.db.sql(
		"""
		UPDATE `tabSite Backup`
		SET `database_file` = `database`, `database_url` = `url`, `database_size` = `size`
		WHERE `database` IS NOT NULL
	"""
	)
