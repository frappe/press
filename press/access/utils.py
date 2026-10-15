import frappe


def is_public_resource(doctype: str, docname: str) -> bool:
	if not frappe.get_meta(doctype).has_field("public"):
		return False

	return bool(frappe.get_value(doctype, docname, "public"))
