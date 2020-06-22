# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
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
		frappe.get_doc("Site", domain.site).set_host_name(domain.domain)
