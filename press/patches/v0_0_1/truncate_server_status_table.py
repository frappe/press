# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	frappe.db.sql("TRUNCATE `tabServer Status`")
