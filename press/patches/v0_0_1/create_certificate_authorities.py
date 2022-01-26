# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from press.install import create_certificate_authorities


def execute():
	frappe.reload_doc("press", "doctype", "certificate_authority")
	if frappe.get_site_config().developer_mode:
		frappe.conf.developer_mode = 1
	create_certificate_authorities()
	frappe.conf.developer_mode = 0
