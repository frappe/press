# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe


@frappe.whitelist()
def all():
	sites = frappe.get_list(
		"Site",
		fields=["count(1) as count", "status"],
		order_by="creation desc",
		group_by="status",
	)
	return {"sites": sites}
