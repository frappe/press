# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	frappe.reload_doctype("Team")
	frappe.db.sql(
		"""
		UPDATE tabTeam
		SET payment_mode = 'Card'
		WHERE IFNULL(default_payment_method, '') != ''
		"""
	)

	frappe.db.sql(
		"""
		UPDATE tabTeam
		SET payment_mode = 'Prepaid Credits'
		WHERE IFNULL(payment_mode, '') == ''
		AND name in (
			SELECT team
			FROM `tabBalance Transaction`
			WHERE source in ('Prepaid Credits', 'Transferred Credits')
		)
		"""
	)
