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
def is_valid(keys):
	keys = frappe.parse_json(keys)

	invalid = []
	blacklisted = get_client_blacklisted_keys()

	for key in keys:
		if key in blacklisted:
			invalid.append(key)

	return set(invalid)
