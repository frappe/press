# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "cluster")
	cluster = frappe.get_doc({"doctype": "Cluster", "name": "Default", "default": True})
	cluster.insert()
	doctypes = ["Server", "Proxy Server", "Database Server", "Bench", "Site"]
	for doctype in doctypes:
		frappe.reload_doc("press", "doctype", frappe.scrub(doctype))
		frappe.db.set_value(doctype, {"name": ("like", "%")}, "cluster", "Default")
