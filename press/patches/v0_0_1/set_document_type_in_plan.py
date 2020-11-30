# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "plan")
	frappe.db.sql('update tabPlan set document_type = "Site", `interval` = "Daily"')
