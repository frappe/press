# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.sql(
		"UPDATE `tabMarketplace App` SET show_for_first_site_creation = show_for_site_creation"
	)
