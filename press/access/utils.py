import frappe


def is_public_resource(doctype: str, docname: str) -> bool:
	def bench(bench: str):
		release_group = frappe.get_value("Bench", bench, "group")
		return frappe.get_value("Release Group", release_group, "public")

	if doctype == "Bench":
		return bench(docname)

	if not frappe.get_meta(doctype).has_field("public"):
		return False

	return bool(frappe.get_value(doctype, docname, "public"))
