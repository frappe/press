from typing import Any

import frappe

from press.guards import role_guard

# Any team member can answer a support access request, so its notification is for everyone.
UNRESTRICTED_TYPES = ("Support Access",)


def check(document_name: str) -> bool:
	notification: Any = frappe.db.get_value(
		"Press Notification", document_name, ["type", "reference_doctype", "reference_name"], as_dict=True
	)
	if not notification:
		return False
	if notification.type in UNRESTRICTED_TYPES:
		return True
	return permits_reference(notification.reference_doctype, notification.reference_name)


def permits_reference(reference_doctype: str | None, reference_name: str | None) -> bool:
	# Notifications about other documents have no Press Role to grant them.
	if reference_doctype not in (*role_guard.LIMITED_DOCTYPES, "Database Server") or not reference_name:
		return False
	return bool(role_guard.check(reference_doctype, reference_name))


def restrict_to_roles(query):
	"""Keep only the notifications about documents the Press Roles of the user permit."""
	if not role_guard.is_restricted():
		return query
	PressNotification = frappe.qb.DocType("Press Notification")
	condition = PressNotification.type.isin(UNRESTRICTED_TYPES)
	for document_type in role_guard.LIMITED_DOCTYPES:
		condition |= permitted_reference(document_type)
	return query.where(condition | permitted_database_server())


def permitted_reference(document_type: str):
	PressNotification = frappe.qb.DocType("Press Notification")
	is_type = PressNotification.reference_doctype == document_type
	permitted = role_guard.permitted_condition(document_type, PressNotification.reference_name)
	return is_type if permitted is None else is_type & permitted


def permitted_database_server():
	"""A database server takes the grants of its app servers, as in `role_guard.database_server`."""
	PressNotification = frappe.qb.DocType("Press Notification")
	is_type = PressNotification.reference_doctype == "Database Server"
	Server = frappe.qb.DocType("Server")
	permitted = role_guard.permitted_condition("Server", Server.name)
	if permitted is None:
		return is_type
	primaries, replicas = granted_database_servers(Server, permitted)
	return is_type & (
		PressNotification.reference_name.isin(primaries) | PressNotification.reference_name.isin(replicas)
	)


def granted_database_servers(Server, permitted):
	"""Subqueries for the primaries of the permitted app servers, and for the replicas of those primaries."""
	DatabaseServer = frappe.qb.DocType("Database Server")
	primaries = frappe.qb.from_(Server).select(Server.database_server).where(permitted)
	replicas = (
		frappe.qb.from_(DatabaseServer)
		.select(DatabaseServer.name)
		.where(DatabaseServer.primary.isin(primaries))
	)
	return primaries, replicas
