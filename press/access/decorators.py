import functools

import frappe
from frappe.model.document import Document

from .support_access import can_perform


def action_guard(action: str):
	"""
	Decorator to guard actions based on team permissions and access rules. This
	decorator should only be used with instance methods of classes that inherit
	from frappe.Document. It validates permissions before allowing the
	decorated method to execute.
	"""

	def throw_err():
		msg = "You do not have permission to perform this action"
		frappe.throw(msg, frappe.PermissionError)

	def decorator(fn):
		@functools.wraps(fn)
		def wrapper(instance: Document, *args, **kwargs):
			team = getattr(instance, "team", None)
			if not can_perform(instance.doctype, str(instance.name), team, action):
				throw_err()
			return fn(instance, *args, **kwargs)

		return wrapper

	return decorator
