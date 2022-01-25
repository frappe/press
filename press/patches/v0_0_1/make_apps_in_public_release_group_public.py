# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doctype("Release Group")
	frappe.reload_doctype("Frappe App")
	groups = frappe.get_all("Release Group", filters={"public": True})
	for group in groups:
		for app in frappe.get_doc("Release Group", group.name).apps:
			frappe.db.set_value("Frappe App", app.app, "public", True)
