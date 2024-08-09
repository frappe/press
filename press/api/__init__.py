import frappe

from press.utils import get_minified_script, get_minified_script_2
from press.saas.doctype.product_trial_request.product_trial_request import (
	get_app_trial_page_url,
)


@frappe.whitelist(allow_guest=True)
def script():
	return get_minified_script()


@frappe.whitelist(allow_guest=True)
def script_2():
	return get_minified_script_2()


@frappe.whitelist(allow_guest=True)
def handle_suspended_site_redirection():
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = get_app_trial_page_url() or "/dashboard"
