# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("App Release")

	frappe.db.sql(
		"""
		UPDATE
			`tabApp Release`
		SET
			status = 'Draft'
		WHERE
			IFNULL(status, '') = ''
	"""
	)
