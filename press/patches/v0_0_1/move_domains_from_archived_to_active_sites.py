# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	domains = frappe.get_all(
		"Site Domain",
		fields=["site", "domain", "name"],
		filters={"status": "Active", "site": ("like", "%.archived%")},
	)
	for domain in domains:
		archived_site = frappe.get_value(
			"Site", domain.site, ["status", "subdomain", "team"], as_dict=True
		)

		if archived_site.status != "Archived":
			continue

		active_site = frappe.db.get_value(
			"Site",
			{"subdomain": archived_site.subdomain, "status": ("!=", "Archived")},
			["name", "team"],
			as_dict=True,
		)
		if active_site and archived_site.team == active_site.team:
			frappe.db.set_value("Site Domain", domain.name, "site", active_site.name)
