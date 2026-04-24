import frappe
from frappe.core.utils import find

from press.saas.api import whitelist_saas_api
from press.utils.dns import check_dns_cname_a


@whitelist_saas_api
def get_domains() -> list:
	site_name = frappe.local.site_name
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


@whitelist_saas_api
def check_dns(domain: str) -> dict:
	return check_dns_cname_a(frappe.local.site_name, domain)


@whitelist_saas_api
def add_domain(domain: str):
	frappe.get_doc("Site", frappe.local.site_name).add_domain(domain)


@whitelist_saas_api
def remove_domain(domain: str):
	frappe.get_doc("Site", frappe.local.site_name).remove_domain(domain)


@whitelist_saas_api
def retry_add_domain(domain: str):
	frappe.get_doc("Site", frappe.local.site_name).retry_add_domain(domain)


@whitelist_saas_api
def set_host_name(domain: str):
	frappe.get_doc("Site", frappe.local.site_name).set_host_name(domain)


@whitelist_saas_api
def set_redirect(domain: str):
	frappe.get_doc("Site", frappe.local.site_name).set_redirect(domain)


@whitelist_saas_api
def unset_redirect(domain: str):
	frappe.get_doc("Site", frappe.local.site_name).unset_redirect(domain)


@whitelist_saas_api
def get_inbound_ip() -> str:
	return frappe.get_cached_doc("Site", frappe.local.site_name).inbound_ip
