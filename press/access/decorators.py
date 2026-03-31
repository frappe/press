import functools

import frappe
from frappe.model.document import Document

from press.utils import get_current_team

from .actions import ACTIONS_RULES
from .support_access import has_support_access


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
			if frappe.local.system_user():
				return fn(instance, *args, **kwargs)

			current_team = get_current_team()
			instance_team = getattr(instance, "team", None)

			if instance_team and instance_team == current_team:
				return fn(instance, *args, **kwargs)

			if has_support_access(instance.doctype, instance.name, action):
				return fn(instance, *args, **kwargs)

			doctype_rules = ACTIONS_RULES.get(instance.doctype, {})
			action_allowed = doctype_rules.get(action, True)
			if not action_allowed:
				throw_err()

			return fn(instance, *args, **kwargs)

		return wrapper

	return decorator
