# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def new(name):
	app = frappe.get_doc({"doctype": "Frappe App", "name": name})
	app.insert()
	return app


@frappe.whitelist()
def get(name):
	app = frappe.get_doc("Frappe App", name)
	return {"name": app.name, "url": app.url, "releases": [], "deploys": []}


@frappe.whitelist()
def all():
	apps = frappe.get_all("Frappe App", fields=["name", "url"])
	return apps
