import functools

import frappe

from press.utils.user import is_beta_tester


def beta_testing():
	"""
	Decorator to mark a function as a beta feature. Only beta testers will be
	able to access the function.
	"""

	def wrapped(func):
		@functools.wraps(func)
		def inner(*args, **kwargs):
			if is_beta_tester():
				return func(*args, **kwargs)
			return frappe.throw("This feature is only available for beta testers", frappe.ValidationError)

		return inner

	return wrapped
