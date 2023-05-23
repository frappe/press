import frappe


def execute():
	frappe.reload_doctype("Press Settings")
	settings = frappe.get_single("Press Settings")
	try:
		settings.get_password("press_monitoring_password")
	except frappe.AuthenticationError:
		settings.press_monitoring_password = frappe.generate_hash()
		settings.save()
