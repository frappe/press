# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	doctypes = ["Server", "Proxy Server", "Database Server"]
	for doctype in doctypes:
		frappe.reload_doc("press", "doctype", frappe.scrub(doctype))
		servers = frappe.get_all(doctype, {"hostname": ("is", "not set")})
		domain = frappe.db.get_single_value("Press Settings", "domain")
		for server in servers:
			hostname = server.name.replace(f".{domain}", "")
			frappe.db.set_value(doctype, server.name, "hostname", hostname)
			frappe.db.set_value(doctype, server.name, "domain", domain)
