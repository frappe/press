# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe


def execute():

	root_domain = frappe.get_single_value("Press Settings", "domain")
	frappe.db.set_value(
		"Blocked Domain", {"root_domain": ("is", "not set")}, "root_domain", root_domain
	)
