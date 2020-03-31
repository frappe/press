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
def all():
	groups = frappe.get_all("Release Group", filters={"owner": frappe.session.user})
	if groups:
		group = groups[0]
		group = frappe.get_doc("Release Group", group.name)
		return group
	else:
		return []
