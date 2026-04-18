from functools import wraps

import frappe
from frappe.core.utils import find

from press.api.developer.marketplace import DeveloperApiHandler
from press.utils.dns import check_dns_cname_a


def validate_secret_key(func):
	"""Validate secret_key and inject site_name into the wrapped function."""

	@wraps(func)
	def wrapper(secret_key: str, **kwargs):
		site_name = DeveloperApiHandler(secret_key).app_subscription_doc.site
		return func(site_name=site_name, **kwargs)

	return wrapper


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def get_domains(site_name: str) -> list:
	domains = frappe.get_all(
		"Site Domain",
		fields=["name", "domain", "status", "retry_count", "redirect_to_primary"],
		filters={"site": site_name},
	)
	host_name = frappe.db.get_value("Site", site_name, "host_name")
	primary = find(domains, lambda x: x.domain == host_name)
	if primary:
		primary.primary = True
	domains.sort(key=lambda domain: not domain.get("primary"))
	return domains


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def check_dns(site_name: str, domain: str) -> dict:
	return check_dns_cname_a(site_name, domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def add_domain(site_name: str, domain: str):
	frappe.get_doc("Site", site_name).add_domain(domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def remove_domain(site_name: str, domain: str):
	frappe.get_doc("Site", site_name).remove_domain(domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def retry_add_domain(site_name: str, domain: str):
	frappe.get_doc("Site", site_name).retry_add_domain(domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def set_host_name(site_name: str, domain: str):
	frappe.get_doc("Site", site_name).set_host_name(domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def set_redirect(site_name: str, domain: str):
	frappe.get_doc("Site", site_name).set_redirect(domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def unset_redirect(site_name: str, domain: str):
	frappe.get_doc("Site", site_name).unset_redirect(domain)


@frappe.whitelist(allow_guest=True)
@validate_secret_key
def get_inbound_ip(site_name: str, domain: str):
	return frappe.get_cached_doc("Site", site_name).inbound_ip
