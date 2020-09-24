# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe

no_cache = True


def get_context(context):
	app = frappe.get_doc("Marketplace App", frappe.form_dict.app)
	context.app = app
	if app.category:
		context.category = frappe.get_doc("Marketplace App Category", app.category)
