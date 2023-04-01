# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.reload_doctype("Stripe Payment Method")
	frappe.db.sql(
		"""
		UPDATE `tabStripe Payment Method`
		SET org = team
		"""
	)
