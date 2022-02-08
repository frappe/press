# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from press.press.doctype.site.site import delete_logs


def execute():
	archived_sites = frappe.get_all("Site", filters={"status": "Archived"})
	for site in archived_sites:
		delete_logs(site.name)
