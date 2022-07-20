# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doc("press", "doctype", "team")
	rename_field("Team", "transaction_currency", "currency")
