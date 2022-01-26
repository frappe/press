# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doctype("App Release")
	benches = frappe.get_all(
		"Bench", fields=["name", "candidate"], filters={"status": ("!=", "Archived")}
	)
	candidates = list(set(bench.candidate for bench in benches))
	for candidate in candidates:
		for app in frappe.get_doc("Deploy Candidate", candidate).apps:
			frappe.db.set_value("App Release", app.release, "status", "Approved")
			frappe.db.set_value("App Release", app.release, "deployable", 1)
