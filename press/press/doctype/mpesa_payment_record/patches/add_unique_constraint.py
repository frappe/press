import frappe


def execute():
	frappe.reload_doc("press", "doctype", "mpesa_payment_record")
	frappe.get_doc("DocType", "Mpesa Payment Record").run_module_method("on_doctype_update")
