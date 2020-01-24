# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.password import get_decrypted_password


@frappe.whitelist()
def new(site):
	site = frappe.get_doc(
		{"doctype": "Site", "name": f"{site['name']}.frappe.cloud"}
	).insert(ignore_permissions=True)
	return {
		"name": site.name,
		"password": get_decrypted_password("Site", site.name, "password"),
	}

@frappe.whitelist()
def available():
	bench = frappe.get_all("Bench", limit=1)[0].name
	apps = frappe.get_all("Installed App", fields=["app"], filters={"parent": bench}, order_by="idx")
	return {"name": bench, "apps": [app.app for app in apps]}

@frappe.whitelist()
def all():
	sites = frappe.get_all(
		"Site", fields=["name", "status"], filters={"owner": frappe.session.user}
	)
	return sites


@frappe.whitelist()
def get(name):
	site = frappe.get_doc("Site", name)
	apps = [{"name": app.app} for app in site.apps]
	return {
		"name": site.name,
		"status": site.status,
		"apps": apps,
	}
