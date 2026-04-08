import frappe

from press.guards import role_guard
from press.guards.role_guard.document import has_user_permission
from press.utils import get_current_team


@frappe.whitelist()
def get_notifications(
	filters: dict | None = None,
	limit_start=0,
	limit_page_length=20,
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
		)
		.where(PressNotification.team == get_current_team())
		.orderby(PressNotification.creation, order=frappe.qb.desc)
		.limit(limit_page_length)
		.offset(limit_start)
	)

	if role_guard.is_restricted():
		if not has_user_permission("Site"):
			query = apply_permission_filter(query, "Site", PressNotification)
		if not has_user_permission("Release Group"):
			query = apply_permission_filter(query, "Release Group", PressNotification)

	if filters.get("read") == "Unread":
		query = query.where(PressNotification.read == 0)

	notifications = query.run(as_dict=True)

	for notification in notifications:
		assign_notification_route(notification)

	return notifications


def assign_notification_route(notification):
	if notification.document_type == "Deploy Candidate":
		rg_name = frappe.db.get_value("Deploy Candidate", notification.document_name, "group")
		notification.route = f"groups/{rg_name}/deploys/{notification.document_name}"
	elif notification.document_type == "Agent Job":
		site_name = frappe.db.get_value("Agent Job", notification.document_name, "site")
		notification.route = (
			f"sites/{site_name}/insights/jobs/{notification.document_name}" if site_name else None
		)
	elif notification.document_type == "Support Access":
		notification.route = "access-requests"
	else:
		notification.route = None


def apply_permission_filter(query, doctype, PressNotification):
	permitted = role_guard.permitted_documents(doctype)
	if not permitted:
		query = query.where(PressNotification.document_type != doctype)
	else:
		query = query.where(PressNotification.document_name.isin(permitted))
	return query


@frappe.whitelist()
def mark_all_notifications_as_read():
	frappe.db.set_value("Press Notification", {"team": get_current_team()}, "read", 1, update_modified=False)


@frappe.whitelist()
def get_unread_count():
	return frappe.db.count("Press Notification", {"read": False, "team": get_current_team()})
