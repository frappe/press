# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	from_doctype = "Release Group Frappe App"
	to_doctype = "Release Group Application"
	if frappe.db.table_exists(from_doctype) and not frappe.db.table_exists(to_doctype):
		frappe.rename_doc("DocType", from_doctype, to_doctype, force=True)

	frappe.reload_doctype("Release Group Application")
	rename_field("Release Group Application", "app", "application")
