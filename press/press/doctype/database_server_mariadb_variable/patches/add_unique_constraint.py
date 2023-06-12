# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "database_server_mariadb_variable")
	frappe.get_doc("DocType", "Database Server MariaDB Variable").run_module_method(
		"on_doctype_update"
	)
