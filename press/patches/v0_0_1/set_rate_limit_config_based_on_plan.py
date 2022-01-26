# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from press.press.doctype.plan.plan import get_plan_config
from press.utils import log_error


def execute():
	sites = frappe.get_all(
		"Site", fields=["name", "plan"], filters={"status": ("!=", "Archived")}
	)
	for site in sites:
		if not site.plan:
			continue
		plan_config = get_plan_config(site.plan)
		site_doc = frappe.get_doc("Site", site)
		try:
			site_doc.update_site_config(plan_config)
		except Exception:
			log_error("Rate Limit Patch Failure", site=site.name)
