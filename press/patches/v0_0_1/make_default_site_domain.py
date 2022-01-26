# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site")
	frappe.reload_doc("press", "doctype", "site_domain")
	for site in frappe.db.get_all("Site", {"status": ("!=", "Archived")}, pluck="name"):
		frappe.get_doc("Site", site)._create_default_site_domain()
