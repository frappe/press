import functools

import frappe

REDACTED = "[REDACTED]"
MAX_DEPTH = 20


def system_manager_only(fn):
	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		frappe.only_for("System Manager")
		return fn(*args, **kwargs)

	return wrapper
