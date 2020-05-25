# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from press.press.doctype.site.site import release_name


def execute():
	frappe.reload_doc("press", "doctype", "site")
	sites = frappe.get_all("Site", filters={"status": "Archived"})
	for site in sites:
		release_name(site.name)
		frappe.db.commit()
