# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.sql(
		"UPDATE `tabPress Role` SET allow_billing = enable_billing, allow_apps = enable_apps"
	)
