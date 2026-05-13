from functools import wraps

import frappe


def disabled(fn):
	"""
	Decorator to disable a function or method. Raises permission error when
	called.
	"""

	@wraps(fn)
	def wrapper(*args, **kwargs):
		frappe.throw("This method is disabled", frappe.PermissionError)

	return wrapper
