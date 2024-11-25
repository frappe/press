# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("Drip Email")
	frappe.db.sql("UPDATE `tabDrip Email` SET message_html = message, content_type = 'HTML'")
