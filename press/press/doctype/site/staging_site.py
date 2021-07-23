# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

from datetime import datetime, timedelta

import frappe
from frappe.model.naming import make_autoname

from press.press.doctype.site.site import Site
from press.utils import log_error


class StagingSite(Site):
	def __init__(self, bench_name: str):
		bench = frappe.get_doc("Bench", bench_name)
		plan = frappe.db.get_value("Press Settings", None, "staging_plan")
		if not plan:
			frappe.throw("Staging plan not set in settings")
			log_error(title="Staging plan not set in settings")
		super().__init__(
			{
				"doctype": "Site",
				"subdomain": make_autoname("staging-.########"),
				"staging": True,
				"bench": bench_name,
				"apps": [{"app": app.app} for app in bench.apps],
				"team": "Administrator",
				"subscription_plan": plan,
			}
		)


def archive_expired_sites():
	expiry = frappe.db.get_value("Press Settings", None, "staging_expiry") or 24
	sites = frappe.get_all(
		"Site", {"staging": True, "created_on": ("<", datetime.now() - timedelta(expiry))}
	)
	for site_name in sites:
		site = frappe.doc("Site", site_name)
		site.archive()
