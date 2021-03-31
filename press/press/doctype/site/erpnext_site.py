# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
from press.utils import get_current_team
from press.press.doctype.site.site import Site
import frappe

# TODO: change back to "erpnext.com"
ERPNEXT_DOMAIN = "frappe.cloud"
# ERPNEXT_APPS = ["frappe", "erpnext", "erpnext_support"]
ERPNEXT_APPS = ["frappe", "erpnext"]
ERPNEXT_PLAN = "Free"
# ERPNEXT_PLAN = "USD 25"


class ERPNextSite(Site):
	def __init__(self, subdomain, team):
		# TODO: remove hardcoding
		group = "bench-0001"

		super().__init__(
			{
				"doctype": "Site",
				"subdomain": subdomain,
				"domain": ERPNEXT_DOMAIN,
				"bench": self.get_bench(group),
				"apps": [{"app": app} for app in ERPNEXT_APPS],
				"team": team.name,
				"free": team.free_account,
				"subscription_plan": ERPNEXT_PLAN,
				"trial_end_date": frappe.utils.add_date(None, 14)
			}
		)

	def after_insert(self):
		super().after_insert()
		self.create_subscription(ERPNEXT_PLAN)

	def get_bench(self, release_group):
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
				bench.status = "Active" AND bench.group = %s
			ORDER BY
				server.use_for_new_sites DESC, bench.creation DESC
			LIMIT 1
		"""
		return frappe.db.sql(query, [release_group], as_dict=True)[0].name

	def can_create_site(self):
		return True
