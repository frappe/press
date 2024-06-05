# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors

from __future__ import unicode_literals
import frappe


def execute():
	# update_usd_invoices()
	# update_amount_due_with_tax_field()
	update_draft_invoices()


def update_draft_invoices():
	invoices = frappe.db.get_all(
		"Invoice",
		filters={
			"type": "Subscription",
			"status": ("in", ["Draft", "Unpaid"]),
			"currency": "INR",
			"total": (">", 0),
			"period_end": (
				"between",
				# gst was applied from Nov 2023 and we dont want to touch current draft invoices
				["2023-11-30", "2024-05-31"],
			),
		},
		pluck="name",
	)
	for inv_id in invoices:
		savepoint_name = f"update_invoice_{inv_id}"
		try:
			frappe.db.savepoint(savepoint_name)

			invoice = frappe.get_doc("Invoice", inv_id)
			if invoice.applied_credits == 0:
				invoice.calculate_total()
				invoice.amount_due = invoice.total
				invoice.apply_taxes_if_applicable()
				invoice.save()
				if invoice.stripe_invoice_id:
					stripe_invoice = invoice.get_stripe_invoice()
					if stripe_invoice.status == "open":
						# void invoice with incorrect amount
						invoice.change_stripe_invoice_status("Void")
						invoice.stripe_invoice_id = None
						invoice.save()
						# create new invoice
						invoice.finalize_invoice()
					else:
						log_failure(inv_id, "Stripe invoice status is not open")
			else:
				# applied credits > 0
				pass

		except Exception:
			frappe.db.rollback(save_point=savepoint_name)
			log_failure(inv_id, frappe.get_traceback())


def log_failure(inv_id, message):
	pass
