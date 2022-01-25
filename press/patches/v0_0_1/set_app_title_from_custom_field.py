# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "app")
	apps = frappe.get_all("App", ["name", "_title"], {"title": ("is", "not set")})
	for app in apps:
		frappe.db.set_value("App", app.name, "title", app._title)
