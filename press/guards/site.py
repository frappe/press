import functools

import frappe


def feature(key: str, site_key: str = "site", raise_error: bool = True):
	def get_site() -> str:
		return (frappe.request.json or frappe.request.form).get(site_key)

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			[plan, is_free] = frappe.get_value("Site", get_site(), ["plan", "free"])
			if is_free or frappe.get_value("Site Plan", plan, key):
				return fn(*args, **kwargs)
			if raise_error:
				message = "Current plan does not support this feature."
				frappe.throw(message, frappe.PermissionError)
			return None

		return inner

	return wrapper
