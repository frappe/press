# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe
from frappe.model.meta import trim_tables


def execute():
	frappe.reload_doc("press", "doctype", "team")
	trim_tables("Stripe Payment Method")
