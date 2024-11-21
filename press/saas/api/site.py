# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.api import site as site_api
from press.saas.api import whitelist_saas_api


@whitelist_saas_api
def info():
	site = frappe.get_value("Site", frappe.local.site_name, ["plan", "trial_end_date"], as_dict=True)
	return {
		"name": frappe.local.site_name,
		"trial_end_date": frappe.get_value("Site", frappe.local.site_name, "trial_end_date"),
		"plan": frappe.get_doc("Site Plan", site.plan),
	}


@whitelist_saas_api
def change_plan(plan: str):
	site = frappe.local.get_site()
	site.set_plan(plan)


@whitelist_saas_api
def get_plans():
	site = frappe.get_value("Site", frappe.local.site_name, ["server", "group", "plan"], as_dict=True)
	is_site_on_private_bench = frappe.db.get_value("Release Group", site.group, "public") is False
	is_site_on_shared_server = frappe.db.get_value("Server", site.server, "public")
	plans = site_api.get_site_plans()
	filtered_plans = []

	for plan in plans:
		if plan.name != site.plan:
			if plan.restricted_plan or plan.is_frappe_plan or plan.is_trial_plan:
				continue
			if is_site_on_private_bench and not plan.private_benches:
				continue
			if plan.dedicated_server_plan and is_site_on_shared_server:
				continue
			if not plan.dedicated_server_plan and not is_site_on_shared_server:
				continue
		filtered_plans.append(plan)

	return filtered_plans


@whitelist_saas_api
def get_first_support_plan():
	plans = get_plans()
	for plan in plans:
		if plan.support_included and not plan.is_trial_plan:
			return plan
	return None
