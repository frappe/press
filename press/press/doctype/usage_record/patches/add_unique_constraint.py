import frappe


def execute():
	frappe.get_doc("DocType", "Usage Record").run_module_method("on_doctype_update")
