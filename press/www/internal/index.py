# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def get_context(context):
	frappe.flags.redirect_location = "/internal/getting-started/overview"
	raise frappe.Redirect
