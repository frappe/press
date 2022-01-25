# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "marketplace_app")
	apps = frappe.get_all("Marketplace App", {"app": ("is", "not set")})
	for app in apps:
		frappe.db.set_value(
			"Marketplace App", app.name, "app", app.name, update_modified=False, modified=False
		)
