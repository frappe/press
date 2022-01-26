# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "release_group")
	frappe.reload_doc("press", "doctype", "release_group_app")
	frappe.reload_doc("press", "doctype", "release_group_server")

	groups = frappe.get_all("Release Group")
	for group in groups:
		old_group_name = group.name
		group = frappe.get_doc("Release Group", group.name)
		group.set_new_name(force=True)
		frappe.rename_doc("Release Group", old_group_name, group.name, force=True)
