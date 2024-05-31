# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


# import frappe

from .dashboard import _get_context

base_template_path = "templates/www/dashboard-old.html"
no_cache = 1


def get_context(context):
	return _get_context()
