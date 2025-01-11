import frappe


def execute():
	frappe.reload_doc("press", "doctype", "usage_record")
	frappe.get_doc("DocType", "Usage Record").run_module_method("on_doctype_update")
