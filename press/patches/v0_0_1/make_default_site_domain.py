# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site")
	for site in frappe.db.get_all("Site", {"status": "Active"}, ["name"]):
		frappe.get_doc("Site", site.name)._create_default_site_domain()
