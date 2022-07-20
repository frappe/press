# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe.utils import update_progress_bar


def execute():
	frappe.reload_doc("press", "doctype", "invoice")
	# only apply to invoices that has credits applied
	invoices = frappe.db.get_all(
		"Invoice", {"docstatus": 1, "applied_credits": (">", 0)}, pluck="name"
	)

	total_invoices = len(invoices)
	for i, inv in enumerate(invoices):
		update_progress_bar("Updating invoices", i, total_invoices)
		invoice = frappe.get_doc("Invoice", inv)
		invoice.compute_free_credits()
		invoice.db_set("free_credits", invoice.free_credits, update_modified=False)
