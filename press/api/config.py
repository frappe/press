import frappe


@frappe.whitelist()
def standard_config_keys():
	return frappe.get_all(
		"Site Config Key",
		fields=["`key`", "title", "type", "description"],
		filters={"internal": False},
	)

