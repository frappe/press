# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	rename_doctypes()
	rename_fields()


def rename_doctypes():
	renames = {
		"SaaS Product": "Product Trial",
		"SaaS Product App": "Product Trial App",
		"SaaS Product Signup Field": "Product Trial Signup Field",
		"SaaS Product Site Request": "Product Trial Request",
	}
	for from_doctype, to_doctype in renames.items():
		if frappe.db.table_exists(from_doctype) and not frappe.db.table_exists(to_doctype):
			frappe.rename_doc("DocType", from_doctype, to_doctype, force=True)


def rename_fields():
	frappe.reload_doctype("Account Request")
	rename_field("Account Request", "saas_product", "product_trial")

	frappe.reload_doctype("Product Trial Request")
	rename_field("Product Trial Request", "saas_product", "product_trial")
