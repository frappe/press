# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	frappe.get_doc("DocType", "Site Migration").run_module_method("on_doctype_update")
