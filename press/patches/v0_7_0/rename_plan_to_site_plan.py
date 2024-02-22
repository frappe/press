import frappe


def execute():
	from_doctype = "Plan"
	to_doctype = "Site Plan"
	if frappe.db.table_exists(from_doctype) and not frappe.db.table_exists(to_doctype):
		frappe.rename_doc("DocType", from_doctype, to_doctype, force=True)
