# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt
import frappe


def execute():
	frappe.reload_doctype("Site")
	# set setup_wizard_status_check_next_retry_on to current datetime
	# in saas sites that has setup_wizard_complete = false
	# and setup_wizard_status_check_next_retry_on is null

	frappe.db.sql(
		"""
		UPDATE
			tabSite s
		SET
			s.setup_wizard_status_check_next_retry_on = NOW()
		WHERE
			s.setup_wizard_complete = 0
			and s.setup_wizard_status_check_next_retry_on is null
			and s.status != 'Archived'
	"""
	)
