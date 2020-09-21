import frappe
from press.utils import get_client_blacklisted_keys


@frappe.whitelist()
def standard_keys():
	return frappe.get_all(
		"Site Config Key",
		fields=["`key`", "title", "type", "description"],
		filters={"internal": False},
	)

@frappe.whitelist()
def is_valid(key):
	return key not in get_client_blacklisted_keys()
