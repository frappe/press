# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


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
		UPDATE tabTeam t
		LEFT JOIN
			`tabBalance Transaction` b on t.name = b.team
			AND b.source in ('Prepaid Credits', 'Transferred Credits')
		SET
			t.payment_mode = 'Prepaid Credits'
		WHERE
			IFNULL(t.payment_mode, '') = ''
			AND b.source in ('Prepaid Credits', 'Transferred Credits')
		"""
	)
