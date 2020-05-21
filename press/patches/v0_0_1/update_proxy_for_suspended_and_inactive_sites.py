# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils.fixtures import sync_fixtures


def execute():
	sync_fixtures("press")
	sites = frappe.get_all(
		"Site",
		fields=["name", "status"],
		filters={"status": ("in", ("Suspended", "Inactive"))},
	)
	for site in sites:
		site = frappe.get_doc("Site", site.name)
		proxy_status = {"Suspended": "suspended", "Inactive": "deactivated"}
		site.update_site_status_on_proxy(proxy_status[site.status])
