import frappe
from press.utils import get_current_team


@frappe.whitelist()
def get_notifications(filters=None):
	if not filters:
		filters = {}
	return frappe.get_all(
		"Press Notification",
		filters=filters,
		fields=["name", "type", "message", "creation", "read", "route"],
		order_by="creation desc",
	)


@frappe.whitelist()
def mark_notification_as_read(name):
	frappe.db.set_value("Press Notification", name, "read", True)


@frappe.whitelist()
def get_unread_count():
	return frappe.db.count(
		"Press Notification", {"read": False, "team": get_current_team()}
	)
