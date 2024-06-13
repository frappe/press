# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors

from __future__ import unicode_literals
import frappe


def execute():
	renames = {
		"SaaS Product": "Product Trial",
		"SaaS Product App": "Product Trial App",
		"SaaS Product Signup Field": "Product Trial Signup Field",
		"SaaS Product Site Request": "Product Trial Request",
	}
	for from_doctype, to_doctype in renames.items():
		if frappe.db.table_exists(from_doctype) and not frappe.db.table_exists(to_doctype):
			frappe.rename_doc("DocType", from_doctype, to_doctype, force=True)
