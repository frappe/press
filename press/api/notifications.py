import frappe
from press.utils import get_current_team


@frappe.whitelist()
def get_notifications(
	filters=None, order_by="creation desc", limit_start=None, limit_page_length=None
):
	if not filters:
		filters = {}
	if filters.get("read") == "Unread":
		filters["read"] = False
	elif filters.get("read") == "Read":
		filters["read"] = True
	notifications = frappe.get_all(
		"Press Notification",
		filters=filters,
		fields=[
			"name",
			"type",
			"read",
			"title",
			"message",
			"creation",
			"is_addressed",
			"is_actionable",
			"document_type",
			"document_name",
		],
		order_by=order_by,
		start=limit_start,
		limit=limit_page_length,
	)

	for notification in notifications:
		if notification.document_type == "Deploy Candidate":
			rg_name = frappe.db.get_value(
				"Deploy Candidate", notification.document_name, "group"
			)
			notification.route = f"benches/{rg_name}/deploys/{notification.document_name}"
		elif notification.document_type == "Agent Job":
			site_name = frappe.db.get_value("Agent Job", notification.document_name, "site")
			notification.route = (
				f"sites/{site_name}/jobs/{notification.document_name}" if site_name else None
			)
		else:
			notification.route = None

	return notifications


@frappe.whitelist()
def mark_notification_as_read(name):
	frappe.db.set_value("Press Notification", name, "read", True)


@frappe.whitelist()
def get_unread_count():
	return frappe.db.count(
		"Press Notification", {"read": False, "team": get_current_team()}
	)
