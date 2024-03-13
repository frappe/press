import frappe
import markdown


def execute():
	apps = frappe.get_all("Marketplace App", fields=["name", "long_description"])

	for app in apps:
		text = app["long_description"].replace("'", "'")
		html = markdown.markdown(text)
		html = html.replace("\n", "")

		frappe.db.set_value("Marketplace App", app["name"], "long_description", html)
