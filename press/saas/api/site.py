# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api


@whitelist_saas_api
def current_plan():
	return {
		"trial_end_date": frappe.get_value("Site", frappe.local.site_name, "trial_end_date"),
		"plan": frappe.get_doc(
			"Site Plan", frappe.get_value("Site", frappe.local.site_name, "plan")
		),
	}


@whitelist_saas_api
def change_plan(plan: str):
	pass
