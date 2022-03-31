# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe

from press.press.doctype.account_request.account_request import AccountRequest
from press.press.doctype.erpnext_consultant.erpnext_consultant import ERPNextConsultant
from press.press.doctype.site.site import Site


class ERPNextSite(Site):
	def __init__(self, site=None, account_request: AccountRequest = None):
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
					"erpnext_consultant": ERPNextConsultant.get_one_for_country(
						account_request.country
					),
					"trial_end_date": frappe.utils.add_days(None, 14),
				}
			)
			self.create_subscription(get_erpnext_plan())

	def rename_pooled_site(self, account_request):
		self.subdomain = account_request.subdomain
		self.is_standby = False
		self.account_request = account_request.name
		self.trial_end_date = frappe.utils.add_days(None, 14)
		plan = get_erpnext_plan()
		self._update_configuration(self.get_plan_config(plan), save=False)
		self.erpnext_consultant = ERPNextConsultant.get_one_for_country(
			account_request.country
		)
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
