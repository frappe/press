# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe


def execute():
	frappe.db.sql(
		"""UPDATE `tabDynamic Link` SET link_doctype = 'Org' WHERE link_doctype = 'Team'"""
	)
