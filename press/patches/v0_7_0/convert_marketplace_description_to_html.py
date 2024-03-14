import frappe


def execute():
	apps = frappe.get_all("Marketplace App", fields=["name", "long_description"])

	for app in apps:
		html = frappe.utils.md_to_html(app["long_description"])
		frappe.db.set_value("Marketplace App", app["name"], "long_description", html)
