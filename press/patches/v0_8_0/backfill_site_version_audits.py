# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.site_version_audit.site_version_audit import (
	count_sites_by_version_and_age_on,
	save_audit,
)

MONTHS = 12


def execute():
	"""Seed the audit with a year of month ends, rewound from Site Update.

	The daily job only starts recording from today, and the question the
	audit answers -- is the stale tail shrinking -- needs history to be worth
	anything. These rows are marked `backfilled` because they only count sites
	that are still active, so they undercount the further back they go.
	"""
	frappe.reload_doc("press", "doctype", "site_version_audit")

	for months_ago in range(MONTHS, 0, -1):
		month_end = frappe.utils.get_last_day(frappe.utils.add_months(frappe.utils.today(), -months_ago))
		save_audit(str(month_end), count_sites_by_version_and_age_on(month_end), backfilled=True)
