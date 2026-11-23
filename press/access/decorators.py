import functools

import frappe
from frappe import _
from frappe.model.document import Document

from .support_access import can_perform


def action_guard(action: str):
	"""
	Decorator to guard actions based on team permissions and access rules. This
	decorator should only be used with instance methods of classes that inherit
	from frappe.Document. It validates permissions before allowing the
	decorated method to execute.
	"""

	def decorator(fn):
		@functools.wraps(fn)
		def wrapper(instance: Document, *args, **kwargs):
			team = getattr(instance, "team", None)
			ensure_can_perform(instance.doctype, str(instance.name), team, action)
			return fn(instance, *args, **kwargs)

		return wrapper

	return decorator


def ensure_can_perform(doctype: str, docname: str, team: str | None, action: str) -> None:
	"""Refuse `action` on `docname` when the access rules do not allow it."""
	if not can_perform(doctype, docname, team, action):
		frappe.throw(_("You do not have permission to perform this action"), frappe.PermissionError)
