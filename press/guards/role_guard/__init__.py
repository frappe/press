import functools
import inspect
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, Literal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Count
from frappe.query_builder.terms import QueryBuilder, ValueWrapper

from press.utils import get_current_team, is_admin_user, is_team_owner
from press.utils import user as utils_user

from .action import action_key
from .api import api_key
from .bench import check as bench_check
from .database_server import check as database_server_check
from .document import check as document_check
from .document import has_user_permission
from .marketplace import check as marketplace_check
from .notification import check as notification_check
from .server_snapshot import check as server_snapshot_check
from .site_backup import check as site_backup_check
from .webhook import check as webhook_check

# Press Roles can limit a member to some documents of these types.
LIMITED_DOCTYPES = ("Site", "Release Group", "Server")


def api(scope: Literal["billing", "partner"]):
	def wrapper(fn):
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			if (not roles_enabled()) or (skip_roles()) or utils_user.is_system_manager():
				return fn(*args, **kwargs)
			key = api_key(scope)
			if not key:
				return fn(*args, **kwargs)
			team = get_current_team()
			if is_team_owner(team) or is_admin_user(team):
				return fn(*args, **kwargs)
			PressRole = frappe.qb.DocType("Press Role")
			PressRoleUser = frappe.qb.DocType("Press Role User")
			has_permission = (
				frappe.qb.from_(PressRole)
				.inner_join(PressRoleUser)
				.on(PressRoleUser.parent == PressRole.name)
				.select(Count(PressRole.name).as_("count"))
				.where(PressRole.team == team)
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
			if (not roles_enabled()) or (skip_roles()) or utils_user.is_system_manager():
				return fn(self, *args, **kwargs)
			key = action_key(self)
			if not key:
				return fn(self, *args, **kwargs)
			team = get_current_team()
			if is_team_owner(team) or is_admin_user(team):
				return fn(self, *args, **kwargs)
			PressRole = frappe.qb.DocType("Press Role")
			PressRoleUser = frappe.qb.DocType("Press Role User")
			has_permission = (
				frappe.qb.from_(PressRole)
				.inner_join(PressRoleUser)
				.on(PressRoleUser.parent == PressRole.name)
				.select(Count(PressRole.name).as_("count"))
				.where(PressRole.team == team)
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
		@functools.wraps(fn)
		def inner(*args, **kwargs):
			bound_args = inspect.signature(fn).bind(*args, **kwargs)
			bound_args.apply_defaults()
			t = document_type(bound_args.arguments)
			n = document_name(bound_args.arguments)
			r = permits(t, n)
			if not r and default_value:
				return default_value(bound_args.arguments)
			if not r:
				error_message = _("You do not have permission to access this {0}.").format(t)
				frappe.throw(error_message, frappe.PermissionError)
			return fn(*args, **kwargs)

		return inner

	return wrapper


def permits(document_type: str, document_name: str) -> bool:
	"""
	Check whether the Press Roles of the current user allow access to the
	document. Teams without roles allow everything.
	"""
	return (
		(not roles_enabled())
		or skip_roles()
		or utils_user.is_system_manager()
		or bool(check(document_type, document_name))
	)


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


def check(document_type: str, document_name: str) -> bool | list[str]:  # noqa: C901
	"""
	Check if the user has permission to access a specific document type and name.
	"""
	team = get_current_team()
	if is_team_owner(team) or is_admin_user(team):
		return True
	query = base_query()
	match document_type:
		case "Bench":
			return bench_check(query, document_name)
		case "Database Server":
			return database_server_check(query, document_name)
		case "Marketplace App":
			return marketplace_check(query)
		case "Press Notification":
			return notification_check(document_name)
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
	"""Check whether the Press Roles limit which documents the current user sees."""
	return is_plain_member() and not skip_roles()


def is_plain_member() -> bool:
	"""Check whether the user is a member of a team with roles, but not an owner, admin or system manager."""
	team = get_current_team()
	return (
		roles_enabled()
		and not utils_user.is_system_manager()
		and not is_team_owner(team)
		and not is_admin_user(team)
	)


def restricts(document_type: str) -> bool:
	"""Check whether the Press Roles limit the current user to some documents of this type."""
	return is_restricted() and not has_user_permission(document_type)


def permitted_documents(document_type: str) -> list[str]:
	return document_check(base_query(), document_type)


def permitted_condition(document_type: str, field):
	"""Limit `field` to the documents of this type the Press Roles permit, or None when they permit all."""
	if not restricts(document_type):
		return None
	if permitted := permitted_documents(document_type):
		return field.isin(permitted)
	return ValueWrapper(1) == 0  # Hack!


def filter_permitted(query, document_type: str, field):
	"""Keep only rows where `field` is a `document_type` the Press Roles permit."""
	condition = permitted_condition(document_type, field)
	return query if condition is None else query.where(condition)


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


def is_relaxed_mode() -> bool:
	"""
	Check if the current team is in relaxed permissions mode, which allows
	users to bypass role checks if they don't have any roles assigned.
	"""
	return bool(int(frappe.get_value("Team", get_current_team(), "relaxed_permissions")))


def skip_roles() -> bool:
	"""
	Check if the current user has no roles assigned in the current team.
	"""
	if not is_relaxed_mode():
		return False
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	return (
		frappe.qb.from_(PressRole)
		.inner_join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.select(Count(PressRole.name).as_("roles_count"))
		.where(PressRole.team == get_current_team())
		.where(PressRoleUser.user == frappe.session.user)
		.run(as_dict=True)
		.pop()
		.get("roles_count")
		== 0
	)
