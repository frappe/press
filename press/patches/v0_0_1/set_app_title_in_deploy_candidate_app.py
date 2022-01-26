# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	apps = frappe.db.sql(
		"""
		SELECT
			candidate.name, app.title
		FROM
			`tabDeploy Candidate App` candidate
		LEFT JOIN
			`tabApp` app
		ON
			candidate.app = app.name
	""",
		as_dict=True,
	)

	for app in apps:
		frappe.db.set_value("Deploy Candidate App", app.name, "title", app.title)
