# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


@frappe.whitelist()
def after_install():
	frappe.get_doc(
		{"doctype": "Role", "role_name": "Press Admin", "desk_access": 0}
	).insert()
