# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe


def execute():
	frappe.reload_doc("press", "doctype", "deploy_candidate_app")
	frappe.db.sql(
		"""
		UPDATE `tabDeploy Candidate App`
		SET app_name = app
	"""
	)
