# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "invoice")
	invoices = frappe.db.get_all(
		"Invoice",
		{"status": "Paid", "docstatus": 1, "amount_paid": (">", 0), "transaction_amount": 0},
		pluck="name",
	)
	for name in invoices:
		print(f"Updating transaction details for {name}")
		invoice = frappe.get_doc("Invoice", name)
		invoice.flags.skip_frappe_invoice = True
		updated = invoice.update_transaction_details()
		if updated:
			print("✅ Done")
			frappe.db.commit()
