# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "telegram_group_topics")
	frappe.reload_doc("press", "doctype", "telegram_group")
	frappe.reload_doc("press", "doctype", "press_settings")
	settings = frappe.get_doc("Press Settings")
	if settings.telegram_alert_chat_id:
		group = frappe.get_doc(
			{
				"doctype": "Telegram Group",
				"name": "Alerts",
				"chat_id": settings.telegram_alert_chat_id,
			}
		).insert()
		settings.telegram_alerts_chat_group = group.name

	settings.save()
