# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site_backup")
	frappe.db.sql(
		"""
		UPDATE `tabSite Backup`
		SET `database_file` = `database`, `database_url` = `url`, `database_size` = `size`
		WHERE `database_file` IS NOT NULL
	"""
	)
