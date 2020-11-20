# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	from_doctype = "Deploy Candidate App Release"
	to_doctype = "Deploy Candidate Application Release"
	if frappe.db.table_exists(from_doctype) and not frappe.db.table_exists(to_doctype):
		frappe.rename_doc("DocType", from_doctype, to_doctype, force=True)

	frappe.reload_doctype("Deploy Candidate Application Release")
	rename_field("Deploy Candidate Application Release", "app", "application")
