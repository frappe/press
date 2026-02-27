import functools
import inspect
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, Literal

import frappe
from frappe import TYPE_CHECKING, _
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder

if TYPE_CHECKING:
	from press.press.doctype.team.team import Team

from press.utils import get_current_team
from press.utils import user as utils_user

from .action import action_key
from .api import api_key
from .document import check as document_check
from .marketplace import check as marketplace_check
from .server_snapshot import check as server_snapshot_check
from .site_backup import check as site_backup_check
from .webhook import check as webhook_check


def api(scope: Literal["billing", "partner"]):
	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			if (not roles_enabled()) or utils_user.is_system_manager():
				return fn(*args, **kwargs)
			key = api_key(scope)
			if not key:
				return fn(*args, **kwargs)
			team: Team = get_current_team(get_doc=True)
			if team.is_team_owner() or team.is_admin_user():
				return fn(*args, **kwargs)
			PressRole = frappe.qb.DocType("Press Role")
			PressRoleUser = frappe.qb.DocType("Press Role User")
			has_permission = (
				frappe.qb.from_(PressRole)
				.inner_join(PressRoleUser)
				.on(PressRoleUser.parent == PressRole.name)
				.select(Count(PressRole.name).as_("count"))
				.where(PressRole.team == team.name)
				.where(PressRole[key] == 1)
				.where(PressRoleUser.user == frappe.session.user)
				.run(as_dict=True)
				.pop()
				.get("count")
				> 0
			)
			if not has_permission:
				error_message = _("You do not have permission to perform the action.")
				frappe.throw(error_message, frappe.PermissionError)
			return fn(*args, **kwargs)

		return inner

	return wrapper


def action():
	def wrapper(fn):
		@functools.wraps(fn)
		def inner(self: Document, *args, **kwargs):
			if (not roles_enabled()) or utils_user.is_system_manager():
				return fn(self, *args, **kwargs)
			key = action_key(self)
			if not key:
				return fn(self, *args, **kwargs)
			team: Team = get_current_team(get_doc=True)
			if team.is_team_owner() or team.is_admin_user():
				return fn(self, *args, **kwargs)
			PressRole = frappe.qb.DocType("Press Role")
			PressRoleUser = frappe.qb.DocType("Press Role User")
			has_permission = (
				frappe.qb.from_(PressRole)
				.inner_join(PressRoleUser)
				.on(PressRoleUser.parent == PressRole.name)
				.select(Count(PressRole.name).as_("count"))
				.where(PressRole.team == team.name)
				.where(PressRole[key] == 1)
				.where(PressRoleUser.user == frappe.session.user)
				.run(as_dict=True)
				.pop()
				.get("count")
				> 0
			)
			if not has_permission:
				error_message = _("You do not have permission to perform the action.")
				frappe.throw(error_message, frappe.PermissionError)
			return fn(self, *args, **kwargs)

		return inner

	return wrapper


def document(
	document_type: Callable[[OrderedDict], str],
	document_name: Callable[[OrderedDict], str] = lambda _: "",
	default_value: Callable[[OrderedDict], Any] | None = None,
):
	"""
	Check if the user has permission to access a specific document type and
	name. This decorator can inject the result into the decorated function's
	kwargs.

	:param document_type: Document type extractor function
	:param document_name: Document name extractor function
	:param default_value: Return a default value if permission check fails
	"""

	def wrapper(fn):
		def gen_key(document_type: str) -> str:
			return injection_key or document_type.lower().replace(" ", "_") + "s"

		@functools.wraps(fn)
		def inner(*args, **kwargs):
			bound_args = inspect.signature(fn).bind(*args, **kwargs)
			bound_args.apply_defaults()
			t = document_type(bound_args.arguments)
			n = document_name(bound_args.arguments)
			r = (not roles_enabled()) or utils_user.is_system_manager() or check(t, n)
			if not r and default_value:
				return default_value(bound_args.arguments)
			if not r:
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


def check(document_type: str, document_name: str) -> bool | list[str]:
	"""
	Check if the user has permission to access a specific document type and name.
	"""
	team: Team = get_current_team(get_doc=True)
	if team.is_team_owner() or team.is_admin_user():
		return True
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
			return True


def is_restricted() -> bool:
	team = get_current_team(get_doc=True)
	return (
		roles_enabled()
		and not utils_user.is_system_manager()
		and not team.is_team_owner()
		and not team.is_admin_user()
	)


def permitted_documents(document_type: str) -> list[str]:
	return document_check(base_query(), document_type)


def roles_enabled() -> bool:
	"""
	Check if role-based access control is enabled for the current team. This is
	done by checking if any roles exist for the team.
	"""
	return bool(
		frappe.db.exists(
			{
				"doctype": "Press Role",
				"team": get_current_team(),
			}
		)
	)
