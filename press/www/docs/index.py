# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def get_context(context):
	frappe.flags.redirect_location = '/docs/getting-started/overview'
	raise frappe.Redirect
