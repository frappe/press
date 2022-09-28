# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	for machine in frappe.get_all(
		"Virtual Machine", {"status": "Running"}, ["name", "series"]
	):
		server_type_map = {"f": "Server", "m": "Database Server", "n": "Proxy Server"}
		server = frappe.db.get_value(
			server_type_map[machine.series], {"virtual_machine": machine.name}
		)
		frappe.rename_doc("Virtual Machine", machine.name, server)
