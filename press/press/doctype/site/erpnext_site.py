# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from press.press.doctype.site.site import Site
import frappe


class ERPNextSite(Site):
	def __init__(self, site=None, account_request=None):
		if site:
			super().__init__("Site", site)
		elif account_request:
			super().__init__(
				{
					"doctype": "Site",
					"subdomain": account_request.subdomain,
					"domain": get_erpnext_domain(),
					"bench": get_erpnext_bench(),
					"apps": [{"app": app} for app in get_erpnext_apps()],
					"team": "Administrator",
					"account_request": account_request.name,
					"subscription_plan": get_erpnext_plan(),
					"erpnext_consultant": get_erpnext_consultant(account_request.country),
					"trial_end_date": frappe.utils.add_days(None, 14),
				}
			)

	def rename_pooled_site(self, account_request):
		self.subdomain = account_request.subdomain
		self.is_standby = False
		self.account_request = account_request.name
		self.trial_end_date = frappe.utils.add_days(None, 14)
		plan = get_erpnext_plan()
		self._update_configuration(self.get_plan_config(plan), save=False)
		self.erpnext_consultant = get_erpnext_consultant(account_request.country)
		self.save(ignore_permissions=True)
		self.create_subscription(plan)

	def can_change_plan(self):
		return True

	def can_create_site(self):
		return True


def get_erpnext_bench():
	domain = get_erpnext_domain()
	cluster = get_erpnext_cluster()

	proxy_servers = frappe.get_all(
		"Proxy Server",
		[
			["status", "=", "Active"],
			["cluster", "=", cluster],
			["Proxy Server Domain", "domain", "=", domain],
		],
		pluck="name",
	)
	release_group = get_erpnext_group()
	query = """
		SELECT
			bench.name
		FROM
			tabBench bench
		LEFT JOIN
			tabServer server
		ON
			bench.server = server.name
		WHERE
			server.proxy_server in %s AND bench.status = "Active" AND bench.group = %s
		ORDER BY
			server.use_for_new_sites DESC, bench.creation DESC
		LIMIT 1
	"""
	return frappe.db.sql(query, [proxy_servers, release_group], as_dict=True)[0].name


def get_erpnext_domain():
	return frappe.db.get_single_value("Press Settings", "erpnext_domain")


def get_erpnext_plan():
	return frappe.db.get_single_value("Press Settings", "erpnext_plan")


def get_erpnext_group():
	return frappe.db.get_single_value("Press Settings", "erpnext_group")


def get_erpnext_cluster():
	return frappe.db.get_single_value("Press Settings", "erpnext_cluster")


def get_erpnext_apps():
	return [app.app for app in frappe.get_single("Press Settings").erpnext_apps]


def process_setup_erpnext_site_job_update(job):
	if job.status == "Success":
		frappe.db.set_value("Site", job.site, "is_erpnext_setup", True)


def set_erpnext_consultant(country):
	region = frappe.db.get_value("Country", self.country, "region")
	self.erpnext_consultant = self.get_erpnext_consultant(region)
	frappe.db.set_value("Region", region, "last_allocated_to", self.erpnext_consultant)

	def get_erpnext_consultant(self, region):
		erpnext_consultants = frappe.db.sql_list(''' select parent from `tabERPNext Consultant Region`
			where territory = %s ''', region)

		erpnext_consultants = frappe.get_all("ERPNext Consultant", filters={"active": 1,
			"name": ['in', erpnext_consultants]})

		if not erpnext_consultants:
			return ''

		if len(erpnext_consultants) > 1:
			region_details = frappe.get_cached_doc("Region", region)

			erpnext_consultants = [consultant.name for consultant in erpnext_consultants
				if consultant.name!= region_details.last_allocated_to]
		else:
			erpnext_consultants = [erpnext_consultants[0].name]

		return erpnext_consultants[0]

