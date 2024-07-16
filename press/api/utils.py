import frappe


@frappe.whitelist(allow_guest=True)
def get_app_details():
	return {
		"app_logo": frappe.get_website_settings("app_logo") or "default",
		"app_name": frappe.get_website_settings("app_logo") or "default",
		"app_footer_logo": frappe.get_website_settings("app_logo") or "default",
	}
