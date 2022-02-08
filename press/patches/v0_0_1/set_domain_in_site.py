# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site")
	domain = frappe.db.get_single_value("Press Settings", "domain")
	frappe.db.sql(
		"UPDATE tabSite SET domain = %s WHERE IFNULL(domain, '') = ''", (domain,)
	)
