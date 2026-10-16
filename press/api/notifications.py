import frappe
from frappe.query_builder.functions import Count

from press.guards import role_guard
from press.utils import get_current_team

# Any team member can answer a support access request, so its notification is for everyone.
UNRESTRICTED_TYPES = ("Support Access",)

PressNotification = frappe.qb.DocType("Press Notification")


@frappe.whitelist()
def get_notifications(
	filters: dict | None = None,
	limit_start: int = 0,
	limit_page_length: int = 20,
):
	if not filters:
		filters = {}

	query = (
		frappe.qb.from_(PressNotification)
		.select(
			PressNotification.name,
			PressNotification.type,
			PressNotification.read,
			PressNotification.title,
			PressNotification.message,
			PressNotification.creation,
			PressNotification.is_addressed,
			PressNotification.is_actionable,
			PressNotification.document_type,
			PressNotification.document_name,
			PressNotification.reference_name,
			PressNotification["class"],
		)
		.where(PressNotification.team == get_current_team())
		.orderby(PressNotification.creation, order=frappe.qb.desc)
		.limit(limit_page_length)
		.offset(limit_start)
	)

	if filters.get("read") == "Unread":
		query = query.where(PressNotification.read == 0)

	if filters.get("type"):
		query = query.where(PressNotification.type == filters["type"])

	notifications = restrict_to_roles(query).run(as_dict=True)

	for notification in notifications:
		assign_notification_route(notification)

	return notifications


def assign_notification_route(notification):
	if notification.document_type == "Deploy Candidate Build":
		rg_name = frappe.db.get_value("Deploy Candidate Build", notification.document_name, "group")
		notification.route = f"groups/{rg_name}/deploys/{notification.document_name}"
	elif notification.document_type == "Agent Job":
		site_name = frappe.db.get_value("Agent Job", notification.document_name, "site")
		notification.route = (
			f"sites/{site_name}/insights/jobs/{notification.document_name}" if site_name else None
		)
	elif notification.document_type == "Support Access":
		notification.route = "access-requests"
	elif notification.document_type == "Malware Scan":
		notification.route = f"servers/{notification.reference_name}/security"
	else:
		notification.route = None


@frappe.whitelist()
def mark_all_notifications_as_read():
	query = (
		frappe.qb.update(PressNotification)
		.set(PressNotification.read, 1)
		.where(PressNotification.team == get_current_team())
	)
	restrict_to_roles(query).run()


@frappe.whitelist()
def get_unread_count(type: str | None = None):
	query = (
		frappe.qb.from_(PressNotification)
		.select(Count(PressNotification.name))
		.where(PressNotification.team == get_current_team())
		.where(PressNotification.read == 0)
	)

	if type:
		query = query.where(PressNotification.type == type)

	return restrict_to_roles(query).run(pluck=True)[0]


def restrict_to_roles(query):
	"""Keep only the notifications about documents the Press Roles of the user permit."""
	if not role_guard.is_restricted():
		return query
	condition = PressNotification.type.isin(UNRESTRICTED_TYPES)
	for document_type in role_guard.LIMITED_DOCTYPES:
		condition |= permitted_reference(document_type)
	return query.where(condition | permitted_database_server())


def permitted_reference(document_type: str):
	is_type = PressNotification.reference_doctype == document_type
	permitted = role_guard.permitted_condition(document_type, PressNotification.reference_name)
	return is_type if permitted is None else is_type & permitted


def permitted_database_server():
	"""A database server takes the grants of its app servers, as in `role_guard.database_server`."""
	is_type = PressNotification.reference_doctype == "Database Server"
	Server = frappe.qb.DocType("Server")
	permitted = role_guard.permitted_condition("Server", Server.name)
	if permitted is None:
		return is_type
	DatabaseServer = frappe.qb.DocType("Database Server")
	primaries = frappe.qb.from_(Server).select(Server.database_server).where(permitted)
	replicas = (
		frappe.qb.from_(DatabaseServer)
		.select(DatabaseServer.name)
		.where(DatabaseServer.primary.isin(primaries))
	)
	return is_type & (
		PressNotification.reference_name.isin(primaries) | PressNotification.reference_name.isin(replicas)
	)
