# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.sql("UPDATE `tabPayout Order` SET team = recipient")
