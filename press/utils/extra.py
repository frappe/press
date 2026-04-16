from functools import wraps

import frappe
from frappe import _


def disabled(fn):
	"""
	Decorator to disable a function or method. Raises permission error when
	called.
	"""

	@wraps(fn)
	def wrapper(*args, **kwargs):
		frappe.throw(_("This method is disabled"), frappe.PermissionError)

	return wrapper
