# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from press.press.doctype.site.site import Site
import frappe


class ERPNextSite(Site):
	def __init__(self, subdomain, team):
		super().__init__(
			{
				"doctype": "Site",
				"subdomain": subdomain,
				"domain": get_erpnext_domain(),
				"bench": get_erpnext_bench(),
				"apps": [{"app": app} for app in get_erpnext_apps()],
				"team": team.name,
				"free": team.free_account,
				"subscription_plan": get_erpnext_plan(),
				"trial_end_date": frappe.utils.add_days(None, 14),
			}
		)

	def prepare_pooled_site(self, pooled_site, subdomain, team):
		site = frappe.get_doc("Site", pooled_site)
		site.subdomain = subdomain
		site.is_standby = False
		site.team = team.name
		site.free = team.free_account
		site.subscription_plan = get_erpnext_plan()
		site.trial_end_date = frappe.utils.add_days(None, 14)
		site.save()
		site.create_subscription(get_erpnext_plan())

	def after_insert(self):
		super().after_insert()
		self.create_subscription(get_erpnext_plan())

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
