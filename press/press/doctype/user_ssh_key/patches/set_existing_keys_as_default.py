# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("User SSH Key")
	frappe.db.set_value("User SSH Key", {"is_default": False}, "is_default", True)
