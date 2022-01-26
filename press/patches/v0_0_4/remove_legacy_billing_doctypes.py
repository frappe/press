# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	# these doctypes are only deleted from DocType table, their tables will exist
	doctypes = ["Payment", "Payment Ledger Entry"]
	frappe.db.sql("DELETE from tabDocType where name in %s", [doctypes])
