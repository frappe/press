"""Add domains key in press's site configuration (No agent job)."""
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	sites = frappe.get_all("Site", {"status": ("!=", "Archived")}, pluck="name")
	for site_name in sites:
		domains = frappe.get_all(
			"Site Domain",
			{"site": site_name, "name": ("!=", site_name), "status": "Active"},
			pluck="name",
		)
		if not domains:
			continue
		site = frappe.get_doc("Site", site_name)
		site._update_configuration({"domains": domains})
