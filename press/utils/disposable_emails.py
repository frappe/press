import frappe
import requests
from frappe.utils import caching


@caching.redis_cache(ttl=60 * 60)
def domains() -> list[str]:
	"""
	Retrieve a list of disposable email domains.

	:return: A list of disposable email domains.
	"""
	# In test mode, return a mock domain.
	if frappe.flags.in_test:
		return [frappe.mock("domain_name")]
	uri = "https://raw.githubusercontent.com/disposable/disposable-email-domains/master/domains.txt"
	domains_response = requests.get(uri)
	domains_str = domains_response.content.decode("utf-8")
	return domains_str.splitlines()


@caching.redis_cache(ttl=60 * 60)
def is_disposable_provider(domain: str) -> bool:
	"""
	Determine if a given domain is a disposable email provider.

	:param domain: The domain to check.
	:return: True if the domain is disposable, False otherwise.
	"""
	return domain in domains()


def is_disposable(email: str) -> bool:
	"""
	Determine if an email address is from a disposable email provider.

	:param email: The email address to check.
	:return: True if the email is disposable, False otherwise.
	"""
	domain = email.split("@").pop()
	return is_disposable_provider(domain)
