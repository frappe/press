# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	obsolete_doctypes = [
		"Credit Ledger Entry",
		"Custom Domain",
		"Site Analytics",
		"Site History",
		"Site Usage Ledger Entry",
		"Usage Report",
		"User Account",
	]
	for doctype in obsolete_doctypes:
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype)
