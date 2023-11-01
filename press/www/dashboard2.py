# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe

from .dashboard import get_context as _get_context

base_template_path = "templates/www/dashboard2.html"
no_cache = 1


def get_context(context):
	frappe.only_for("System Manager")
	return _get_context(context)
