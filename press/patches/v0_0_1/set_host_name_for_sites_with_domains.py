# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doctype("Site")
	domains = frappe.get_all(
		"Site Domain",
		fields=["site", "domain"],
		filters={"status": "Active"},
		group_by="site",
	)
	for domain in domains:
		site = frappe.get_doc("Site", domain.site)
		if site.status == "Active":
			site.set_host_name(domain.domain)
