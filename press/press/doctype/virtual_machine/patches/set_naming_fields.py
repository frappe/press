# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doc("press", "doctype", "virtual_machine")

	for machine in frappe.get_all(
		"Virtual Machine", ["name", "index", "series", "domain"]
	):
		for server_type, series in [
			("Server", "f"),
			("Database Server", "m"),
			("Proxy Server", "n"),
		]:
			server = frappe.db.get_value(
				server_type, {"virtual_machine": machine.name}, ["name", "domain"], as_dict=True
			)
			if server:
				break
		index = server.name.split("-")[0][1:]
		frappe.db.set_value("Virtual Machine", machine.name, "series", series)
		frappe.db.set_value("Virtual Machine", machine.name, "index", index)
		frappe.db.set_value("Virtual Machine", machine.name, "domain", server.domain)
