# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("Team")
	frappe.db.sql(
		"""
		UPDATE `tabTeam`
		SET team_title = user
		"""
	)
