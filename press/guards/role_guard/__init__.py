import functools
import inspect
from collections import OrderedDict
from collections.abc import Callable

import frappe
from frappe import _
from frappe.query_builder.terms import QueryBuilder

from press.utils import get_current_team

from .document import check as document_check
from .marketplace import check as marketplace_check
from .server_snapshot import check as server_snapshot_check
from .site_backup import check as site_backup_check
from .webhook import check as webhook_check


def for_doc(document_type: Callable[[OrderedDict], str], document_name: Callable[[OrderedDict], str]):
	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			bound_args = inspect.signature(fn).bind(*args, **kwargs)
			bound_args.apply_defaults()
			t = document_type(bound_args.arguments)
			n = document_name(bound_args.arguments)
			if not check(t, n):
				error_message = _("You do not have permission to access this {0}.").format(t)
				frappe.throw(error_message, frappe.PermissionError)
			return fn(*args, **kwargs)

		return inner

	return wrapper


def base_query() -> QueryBuilder:
	"""
	Get a base query for Press Role documents based on the current team context.
	"""
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	return (
		frappe.qb.from_(PressRole)
		.select(PressRole.name)
		.left_join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.where(PressRole.team == get_current_team())
		.where(PressRoleUser.user == frappe.session.user)
	)


def check(document_type: str, document_name: str) -> bool:
	"""
	Check if the user has permission to access a specific document type and name.
	"""
	query = base_query()
	match document_type:
		case "Marketplace App":
			return marketplace_check(query)
		case "Press Webhook":
			return webhook_check(query)
		case "Press Webhook Attempt":
			return webhook_check(query)
		case "Press Webhook Log":
			return webhook_check(query)
		case "Release Group":
			return document_check(query, document_type, document_name)
		case "Server":
			return document_check(query, document_type, document_name)
		case "Server Snapshot":
			return server_snapshot_check(query, document_name)
		case "Site":
			return document_check(query, document_type, document_name)
		case "Site Backup":
			return site_backup_check(query, document_name)
		case _:
			return False
