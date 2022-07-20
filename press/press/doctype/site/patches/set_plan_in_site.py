# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe


def execute():
	# set plan in all non-archived sites that have active subscription
	frappe.reload_doctype("Site")

	frappe.db.sql(
		"""
		UPDATE
			tabSite s
			LEFT JOIN tabSubscription p ON s.name = p.document_name
			AND p.document_type = 'Site'
		SET
			s.plan = p.plan
		WHERE
			s.status != 'Archived'
			and p.enabled = 1
	"""
	)
	# set plan to '' in all sites that have disabled subscription
	frappe.db.sql(
		"""
		UPDATE
			tabSite s
			LEFT JOIN tabSubscription p ON s.name = p.document_name
			AND p.document_type = 'Site'
		SET
			s.plan = ''
		WHERE
			p.enabled = 0
	"""
	)
