# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("Balance Transaction")
	frappe.db.sql(
		"""
		UPDATE `tabBalance Transaction`
		SET org = team
		"""
	)
