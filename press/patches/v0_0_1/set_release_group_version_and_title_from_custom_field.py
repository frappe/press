# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "release_group")
	groups = frappe.get_all(
		"Release Group", ["name", "_title"], {"title": ("is", "not set")}
	)
	for group in groups:
		frappe.db.set_value("Release Group", group.name, "title", group._title)

	groups = frappe.get_all(
		"Release Group", ["name", "_version"], {"version": ("is", "not set")}
	)
	for group in groups:
		frappe.db.set_value("Release Group", group.name, "version", group._version)
