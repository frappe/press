import functools
import inspect
from collections import OrderedDict
from collections.abc import Callable

import frappe
from frappe import TYPE_CHECKING, _
from frappe.model.document import Document

if TYPE_CHECKING:
	from press.press.doctype.team.team import Team


def only_owner(team: Callable[[Document, OrderedDict], str] = lambda document, _: str(document.team)):
	"""
	This guard can only be used for a class method. No other options are
	supported.
	"""

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(self, *args, **kwargs):
			bound_args = inspect.signature(fn).bind(*args, **kwargs)
			bound_args.apply_defaults()
			t = team(self, bound_args.arguments)
			d: Team = frappe.get_cached_doc("Team", t)
			if not d.is_team_owner():
				message = _("Only team owner can perform this action.")
				frappe.throw(message, frappe.PermissionError)
			return fn(self, *args, **kwargs)

		return inner

	return wrapper


def only_admin(team: Callable[[Document, OrderedDict], str] = lambda document, _: str(document.team)):
	"""
	This guard can only be used for a class method. No other options are
	supported. Team owner is considered as admin.
	"""

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(self, *args, **kwargs):
			bound_args = inspect.signature(fn).bind(*args, **kwargs)
			bound_args.apply_defaults()
			t = team(self, bound_args.arguments)
			d: Team = frappe.get_cached_doc("Team", t)
			if not (d.is_team_owner() or d.is_admin_user()):
				message = _("Only team admin can perform this action.")
				frappe.throw(message, frappe.PermissionError)
			return fn(self, *args, **kwargs)

		return inner

	return wrapper


def only_member(
	team: Callable[[Document, OrderedDict], str] = lambda document, _: str(document.team),
	user: Callable[[Document, OrderedDict], str] = lambda _, _args: str(frappe.session.user),
	error_message: str | None = None,
):
	"""
	This guard can only be used for a class method. No other options are
	supported.
	"""

	def wrapper(fn):
		@functools.wraps(fn)
		def inner(self, *args, **kwargs):
			bound_args = inspect.signature(fn).bind(*args, **kwargs)
			bound_args.apply_defaults()
			t = team(self, bound_args.arguments)
			u = user(self, bound_args.arguments)
			if not bool(frappe.db.exists({"doctype": "Team Member", "parent": t, "user": u})):
				message = error_message or _("Only team member can perform this action.")
				frappe.throw(message, frappe.PermissionError)
			return fn(self, *args, **kwargs)

		return inner

	return wrapper
