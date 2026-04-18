import frappe
from frappe.core.utils import find

from press.api.developer.marketplace import DeveloperApiHandler
from press.utils.dns import check_dns_cname_a


def get_site(secret_key: str) -> str:
	return DeveloperApiHandler(secret_key).app_subscription_doc.site


@frappe.whitelist(allow_guest=True)
def get_domains(secret_key: str) -> list:
	site_name = get_site(secret_key)
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
def check_dns(secret_key: str, domain: str) -> dict:
	return check_dns_cname_a(get_site(secret_key), domain)


@frappe.whitelist(allow_guest=True)
def add_domain(secret_key: str, domain: str):
	frappe.get_doc("Site", get_site(secret_key)).add_domain(domain)


@frappe.whitelist(allow_guest=True)
def remove_domain(secret_key: str, domain: str):
	frappe.get_doc("Site", get_site(secret_key)).remove_domain(domain)


@frappe.whitelist(allow_guest=True)
def retry_add_domain(secret_key: str, domain: str):
	frappe.get_doc("Site", get_site(secret_key)).retry_add_domain(domain)


@frappe.whitelist(allow_guest=True)
def set_host_name(secret_key: str, domain: str):
	frappe.get_doc("Site", get_site(secret_key)).set_host_name(domain)


@frappe.whitelist(allow_guest=True)
def set_redirect(secret_key: str, domain: str):
	frappe.get_doc("Site", get_site(secret_key)).set_redirect(domain)


@frappe.whitelist(allow_guest=True)
def unset_redirect(secret_key: str, domain: str):
	frappe.get_doc("Site", get_site(secret_key)).unset_redirect(domain)


@frappe.whitelist(allow_guest=True)
def get_inbound_ip(secret_key: str) -> str:
	return frappe.get_cached_doc("Site", get_site(secret_key)).inbound_ip
