# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def get_context(context):
	frappe.flags.redirect_location = "/internal/getting-started/overview"
	raise frappe.Redirect
