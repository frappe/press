# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
from press.saas.api import whitelist_saas_api
from press.api import site as site_api


@whitelist_saas_api
def info():
	site = frappe.get_value("Site", frappe.local.site_name, ["plan", "trial_end_date"], as_dict=True)
	return {
		"name": frappe.local.site_name,
		"trial_end_date": frappe.get_value("Site", frappe.local.site_name, "trial_end_date"),
		"plan": frappe.get_doc("Site Plan", site.plan)
	}

@whitelist_saas_api
def change_plan(plan: str):
	site = frappe.local.get_site()
	site.set_plan(plan)

@whitelist_saas_api
def get_plans():
	return site_api.get_site_plans()
