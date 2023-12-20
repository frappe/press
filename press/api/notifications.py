import frappe
from press.utils import get_current_team


@frappe.whitelist()
def get_notifications(filters=None):
	if not filters:
		filters = {}
	notifications = frappe.get_all(
		"Press Notification",
		filters=filters,
		fields=[
			"name",
			"type",
			"message",
			"creation",
			"read",
			"document_type",
			"document_name",
		],
		order_by="creation desc",
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
