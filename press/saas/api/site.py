# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.api import site as site_api
from press.saas.api import whitelist_saas_api


@whitelist_saas_api
def info():
	is_fc_user = False
	site = frappe.get_value("Site", frappe.local.site_name, ["plan", "trial_end_date", "team"], as_dict=True)
	site_user = frappe.request.headers.get("x-site-user")

	team_members = frappe.get_doc("Team", site.team).get_user_list()
	if site_user and site_user in team_members:
		is_fc_user = True

	return {
		"is_fc_user": is_fc_user,
		"name": frappe.local.site_name,
		"trial_end_date": site.trial_end_date,
		"plan": frappe.db.get_value("Site Plan", site.plan, ["is_trial_plan"], as_dict=True)
		if site.plan
		else None,
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

	"""
	plans `site_api.get_site_plans()` doesn't include trial plan, as we don't have any roles specified for trial plan
	because from backend only we set the trial plan, end-user can't subscribe to trial plan directly
	If the site is on a trial plan, add it to the starting of the list
	"""

	current_plan = frappe.get_doc("Site Plan", site.plan)
	if current_plan.is_trial_plan:
		filtered_plans.insert(
			0,
			{
				"name": current_plan.name,
				"plan_title": current_plan.plan_title,
				"price_usd": current_plan.price_usd,
				"price_inr": current_plan.price_inr,
				"cpu_time_per_day": current_plan.cpu_time_per_day,
				"max_storage_usage": current_plan.max_storage_usage,
				"max_database_usage": current_plan.max_database_usage,
				"database_access": current_plan.database_access,
				"support_included": current_plan.support_included,
				"offsite_backups": current_plan.offsite_backups,
				"private_benches": current_plan.private_benches,
				"monitor_access": current_plan.monitor_access,
				"dedicated_server_plan": current_plan.dedicated_server_plan,
				"is_trial_plan": current_plan.is_trial_plan,
				"allow_downgrading_from_other_plan": False,
				"clusters": [],
				"allowed_apps": [],
				"bench_versions": [],
				"restricted_plan": False,
			},
		)

	return filtered_plans


@whitelist_saas_api
def get_first_support_plan():
	plans = get_plans()
	for plan in plans:
		if plan.support_included and not plan.is_trial_plan:
			return plan
	return None
