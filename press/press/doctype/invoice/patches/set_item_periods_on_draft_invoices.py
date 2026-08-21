# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Set the billed period on the items of every draft invoice.

	New items get their period from the usage records that come in after this patch.
	Items that already exist would otherwise start from the day of the deploy.
	Submitted invoices keep an empty period, because their descriptions are final.
	"""
	frappe.reload_doc("press", "doctype", "invoice_item")
	invoices = frappe.get_all("Invoice", {"docstatus": 0, "type": "Subscription"}, pluck="name")
	for name in invoices:
		invoice = frappe.get_doc("Invoice", name)
		invoice.set_item_periods()
		for item in invoice.items:
			item.db_update()
		frappe.db.commit()
