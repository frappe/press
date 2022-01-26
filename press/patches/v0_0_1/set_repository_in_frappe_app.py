# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doctype("Frappe App")
	apps = frappe.get_all(
		"Frappe App", fields=["name", "url"], filters={"repo": ("is", "not set")}
	)
	for app in apps:
		repo = app.url.split("/")[-1].replace(".git", "")
		frappe.db.set_value("Frappe App", app.name, "repo", repo)
