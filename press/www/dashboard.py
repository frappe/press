# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def get_context(context):
	if not frappe.request.path.endswith("/"):
		frappe.local.flags.redirect_location = "dashboard/"
		raise frappe.Redirect

	return {"base_template_path": "press/templates/pages/base.html"}
