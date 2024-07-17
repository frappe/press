import frappe


@frappe.whitelist(allow_guest=True)
def get_brand_details():
	return {
		"app_logo": frappe.get_website_settings("app_logo"),
		"app_name": frappe.get_website_settings("app_name"),
		"app_footer_logo": frappe.get_website_settings("footer_logo"),
	}


@frappe.whitelist(allow_guest=True)
def get_app_name():
	return frappe.get_website_settings("app_name") or "Frappe Cloud"
