# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "press_settings")
	press_settings = frappe.get_doc("Press Settings", "Press Settings")
	if not press_settings.cluster:
		press_settings.cluster = frappe.db.get_value(
			"Root Domain", press_settings.domain, "default_cluster"
		)
		press_settings.save()
