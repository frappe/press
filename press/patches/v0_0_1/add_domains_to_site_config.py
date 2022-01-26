# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.utils.fixtures import sync_fixtures


def execute():
	sync_fixtures("press")
	domains = frappe.get_all(
		"Site Domain", fields=["site", "domain", "name"], filters={"status": "Active"},
	)

	for domain in domains:
		site_doc = frappe.get_doc("Site", domain.site)
		site_doc.add_domain_to_config(domain.domain)
