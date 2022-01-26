# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	domains = frappe.get_all(
		"Site Domain", filters={"status": "Active", "site": ("like", "%.archived%")},
	)
	for domain in domains:
		frappe.delete_doc("Site Domain", domain.name)
