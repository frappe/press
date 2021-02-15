# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "app_release")
	sources = frappe.get_all("App Source", {"public": True})
	for source in sources:
		frappe.db.sql(
			"""UPDATE `tabApp Release` SET public = 1 WHERE source = %s""", (source.name)
		)
