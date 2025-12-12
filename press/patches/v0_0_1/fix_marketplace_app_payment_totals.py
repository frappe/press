import frappe
from frappe.utils import flt


def execute():
	"""
	Patch to fix marketplace payout orders and app payment records:
	- Reset all app payment records to 0 since total tracked is incorrect
	- Recalculate totals from submitted payout orders and update app payment records accordingly
	- Submit any draft payout orders
	"""
	reset_app_payment_records()

	# Get all submitted Marketplace payout orders and calculate total and commission amounts from child table to update respective Marketplace App Payment records
	get_totals_from_submitted_payout_orders()

	submit_draft_payout_orders()


def reset_app_payment_records():
	marketplace_app_payment = frappe.qb.DocType("Marketplace App Payment")
	frappe.qb.update(marketplace_app_payment).set(marketplace_app_payment.total_inr, 0).set(
		marketplace_app_payment.total_usd, 0
	).run()
	frappe.db.commit()


def get_totals_from_submitted_payout_orders():
	"""Recalculate total revenue and commission from submitted Marketplace payout orders and set it in Marketplace App Payment record"""
	payout_orders = frappe.get_all(
		"Payout Order",
		filters={"type": "Marketplace", "docstatus": 1},
	)

	for po_data in payout_orders:
		po = frappe.get_doc("Payout Order", po_data.name)

		# Track totals by currency
		commission_inr = 0.0
		commission_usd = 0.0

		# Process each item in the payout order
		for item in po.items:
			if item.currency == "INR":
				commission_inr += flt(item.commission)
			elif item.currency == "USD":
				commission_usd += flt(item.commission)

			update_app_payment_record(
				item.document_name, item.currency, flt(item.total_amount), flt(item.commission)
			)

		# Calculate total commission in recipient currency
		exchange_rate = frappe.db.get_single_value("Press Settings", "usd_rate") or 80
		if po.recipient_currency == "USD":
			inr_in_usd = 0
			if commission_inr > 0:
				inr_in_usd = commission_inr / exchange_rate
			commission = commission_usd + inr_in_usd
		elif po.recipient_currency == "INR":
			commission = commission_inr + (commission_usd * exchange_rate)
		else:
			commission = 0

		# Update the newly added commission field
		frappe.db.set_value("Payout Order", po.name, "commission", commission)


def update_app_payment_record(app_name, currency, item_amount, item_commission):
	app_payment_doc = frappe.get_doc("Marketplace App Payment", app_name)

	if currency == "INR":
		app_payment_doc.total_inr = flt(app_payment_doc.total_inr) + flt(item_amount)
		app_payment_doc.commission_inr = flt(app_payment_doc.commission_inr) + flt(item_commission)
	elif currency == "USD":
		app_payment_doc.total_usd = flt(app_payment_doc.total_usd) + flt(item_amount)
		app_payment_doc.commission_usd = flt(app_payment_doc.commission_usd) + flt(item_commission)

	app_payment_doc.save(ignore_permissions=True)


def submit_draft_payout_orders():
	# Submit any draft Marketplace payout orders
	draft_orders = frappe.get_all(
		"Payout Order", filters={"type": "Marketplace", "docstatus": 0}, fields=["name"]
	)

	for order in draft_orders:
		try:
			po = frappe.get_doc("Payout Order", order.name)
			po.submit()
		except Exception as e:
			frappe.log_error(f"Failed to submit Payout Order {order.name}: {e!s}")
			continue
