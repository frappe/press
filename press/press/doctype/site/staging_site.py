# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
from datetime import datetime, timedelta

import frappe
from frappe.model.naming import make_autoname

from press.press.doctype.site.site import Site


class StagingSite(Site):
	def __init__(self, bench_name: str):
		bench = frappe.get_doc("Bench", bench_name)
		super().__init__(
			{
				"doctype": "Site",
				"subdomain": make_autoname("staging-.########"),
				"staging": True,
				"bench": bench_name,
				"apps": [{"app": app.app} for app in bench.apps],
				"team": "Administrator",
			}
		)


def archive_expired_sites():
	expiry = frappe.db.get_value("Press Settings", None, "staging_site_expiry")
	sites = frappe.get_all(
		"Site", {"staging": True, "created_on": ("<", datetime.now() - timedelta(expiry))}
	)
	for site_name in sites:
		site = frappe.doc("Site", site_name)
		site.archive()
