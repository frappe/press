# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "invoice")
	frappe.reload_doc("press", "doctype", "invoice_item")

	# invoice site usage -> invoice item
	frappe.db.sql(
		"""
		update
			`tabInvoice Item` i,
			`tabInvoice Site Usage` u
		set
			i.document_type = 'Site',
			i.document_name = u.site,
			i.plan = u.plan
		where
			u.parent = i.parent
			and u.idx = i.idx
	"""
	)

	# compute applied_credits
	frappe.db.sql(
		"""
		update
			tabInvoice
		set
			applied_credits = -1 * (starting_balance - ending_balance)
	"""
	)
