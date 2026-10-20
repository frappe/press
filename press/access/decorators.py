import functools

import frappe
from frappe.model.document import Document

from .actions import ACTIONS_RULES
from .support_access import is_insider, outsider_can_access


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
			if is_insider(getattr(instance, "team", None)):
				return fn(instance, *args, **kwargs)
			allowed = ACTIONS_RULES.get(instance.doctype, {}).get(action, True)
			if not outsider_can_access(instance.doctype, str(instance.name), action, allowed):
				throw_err()
			return fn(instance, *args, **kwargs)

		return wrapper

	return decorator
