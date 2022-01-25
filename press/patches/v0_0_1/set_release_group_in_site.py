# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	sites = frappe.db.sql(
		"""
		SELECT
			site.name, bench.group
		FROM
			`tabSite` site
		LEFT JOIN
			`tabBench` bench
		ON
			site.bench = bench.name
	""",
		as_dict=True,
	)

	for site in sites:
		frappe.db.set_value("Site", site.name, "group", site.group)
