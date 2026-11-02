import frappe
from frappe.query_builder.functions import Count

from press.guards.role_guard.notification import restrict_to_roles
from press.press.doctype.press_notification.press_notification import resource_route
from press.utils import get_current_team


@frappe.whitelist()
def get_notifications(
	filters: dict | None = None,
	limit_start: int = 0,
	limit_page_length: int = 20,
):
	if not filters:
		filters = {}

	PressNotification = frappe.qb.DocType("Press Notification")
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
			PressNotification.reference_doctype,
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
	elif notification.type == "Resource Access":
		notification.route = resource_route(notification)
	else:
		notification.route = None


@frappe.whitelist()
def mark_all_notifications_as_read():
	PressNotification = frappe.qb.DocType("Press Notification")
	query = (
		frappe.qb.update(PressNotification)
		.set(PressNotification.read, 1)
		.where(PressNotification.team == get_current_team())
	)
	restrict_to_roles(query).run()


@frappe.whitelist()
def get_unread_count(type: str | None = None):
	PressNotification = frappe.qb.DocType("Press Notification")
	query = (
		frappe.qb.from_(PressNotification)
		.select(Count(PressNotification.name))
		.where(PressNotification.team == get_current_team())
		.where(PressNotification.read == 0)
	)

	if type:
		query = query.where(PressNotification.type == type)

	return restrict_to_roles(query).run(pluck=True)[0]
