# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "server")
	servers = frappe.get_all("Server", {"hostname": ("is", "not set")})
	domain = frappe.db.get_single_value("Press Settings", "domain")
	for server in servers:
		hostname = server.name.replace(f".{domain}", "")
		frappe.db.set_value("Server", server.name, "hostname", hostname)
