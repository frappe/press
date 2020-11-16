# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	frappe.reload_doctype("Release Group Frappe App")
	rename_field("Release Group Frappe App", "app", "application")
