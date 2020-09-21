import frappe


@frappe.whitelist()
def get():
	return frappe.get_all(
		"Site Config Key",
		fields=["key", "title", "type", "description"],
		filters={"internal": False},
	)


@frappe.whitelist()
def new(key, type, title=None, desc=None):
	doc = frappe.get_doc(
		{
			"doctype": "Site Config Key",
			"key": key,
			"title": title,
			"type": type,
			"description": desc,
		}
	).save()
	return doc
