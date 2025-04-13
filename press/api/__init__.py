import frappe

from press.api.client import dashboard_whitelist
from press.utils import get_full_chain_cert_of_domain, get_minified_script, get_minified_script_2, log_error


@frappe.whitelist(allow_guest=True)
def script():
	return get_minified_script()


@frappe.whitelist(allow_guest=True)
def script_2():
	return get_minified_script_2()


@frappe.whitelist(allow_guest=True)
def handle_suspended_site_redirection():
	from press.saas.doctype.product_trial_request.product_trial_request import (
		get_app_trial_page_url,
	)

	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = get_app_trial_page_url() or "/dashboard"


@dashboard_whitelist()
def download_ssl_cert(domain: str):
	if (
		not (domain.endswith("frappe.cloud") or domain.endswith("frappecloud.com"))
		and not frappe.conf.developer_mode
	):
		frappe.throw("Invalid domain provided")

	try:
		return get_full_chain_cert_of_domain(domain)
	except Exception as e:
		log_error("Error downloading SSL certificate", data=e)
		frappe.throw("Failed to download SSL certificate. Please try again later.")
