# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	apps = frappe.db.sql(
		"""
		SELECT
			app.name, `release`.name as 'release'
		FROM
			`tabBench App` app
		LEFT JOIN
			`tabApp Release` `release`
		ON
			(`release`.hash = app.hash AND `release`.source = app.source)
	""",
		as_dict=True,
	)

	for app in apps:
		frappe.db.set_value("Bench App", app.name, "release", app.release)
