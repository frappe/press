# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "cluster")
	cluster = frappe.get_doc({"doctype": "Cluster", "name": "Default", "default": True})
	cluster.insert()
	doctypes = ["Server", "Proxy Server", "Database Server"]
	for doctype in doctypes:
		frappe.reload_doc("press", "doctype", doctype.lower())
		frappe.db.set_value(doctype, None, "cluser", "Default")
