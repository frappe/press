# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "deploy_candidate_difference")
	frappe.reload_doc("press", "doctype", "deploy_candidate_difference_app")
	frappe.reload_doc("press", "doctype", "app_release_difference")

	frappe.db.delete("Deploy Candidate Difference App", {"changed": False})
	differences = frappe.get_all("Deploy Candidate Difference App", "*")
	for difference in differences:
		release_difference = frappe.db.exists(
			"App Release Difference",
			{
				"app": difference.app,
				"source_release": difference.source_release,
				"destination_release": difference.destination_release,
			},
		)
		if not release_difference:
			release_difference_doc = frappe.get_doc(
				{
					"doctype": "App Release Difference",
					"app": difference.app,
					"deploy_type": difference.deploy_type,
					"source": frappe.db.get_value("App Release", difference.source_release, "source"),
					"source_release": difference.source_release,
					"source_hash": difference.source_hash,
					"destination_release": difference.destination_release,
					"destination_hash": difference.destination_hash,
					"files": difference.files,
					"github_diff_url": difference.github_diff_url,
				}
			)
			release_difference_doc.db_insert()
			release_difference = release_difference_doc.name
		frappe.db.set_value(
			"Deploy Candidate Difference App", difference.name, "difference", release_difference
		)
