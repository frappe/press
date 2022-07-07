# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from typing import List, Optional
from frappe.model.document import Document
from press.press.doctype.invoice_item.invoice_item import InvoiceItem
from press.press.doctype.payout_order_item.payout_order_item import PayoutOrderItem


class PayoutOrder(Document):
	def validate(self):
		self.validate_items()
		self.validate_net_totals()

	def validate_items(self):
		for row in self.items:
			invoice_name = row.invoice
			invoice = frappe.db.get_value(
				"Invoice",
				invoice_name,
				["status", "currency", "transaction_amount", "transaction_fee", "exchange_rate"],
				as_dict=True,
			)

			if invoice.status != "Paid":
				frappe.throw(f"Invoice {invoice_name} is not paid yet.")

			transaction_amount = invoice.transaction_amount
			invoice_item = get_invoice_item_for_po_item(invoice_name, row)

			row.tax = row.tax or 0.0
			row.commission = row.commission or 0.0
			row.total_amount = invoice_item.amount
			row.currency = invoice.currency
			row.gateway_fee = 0.0

			if transaction_amount > 0:
				row.gateway_fee = (
					invoice.transaction_fee / transaction_amount
				) * invoice_item.amount
				exchange_rate = invoice.exchange_rate
				if row.currency != "INR" and exchange_rate != 0:
					row.gateway_fee /= exchange_rate

			row.net_amount = row.total_amount - row.tax - row.gateway_fee - row.commission

	def validate_net_totals(self):
		self.net_total_usd = 0
		self.net_total_inr = 0

		for row in self.items:
			if row.currency == "INR":
				self.net_total_inr += row.net_amount
			else:
				self.net_total_usd += row.net_amount

	def before_submit(self):
		if self.mode_of_payment == "Cash" and (not self.frappe_purchase_order):
			frappe.throw(
				"Frappe Purchase Order is required before marking this cash payout as Paid"
			)
		self.status = "Paid"


def get_invoice_item_for_po_item(
	invoice_name: str, payout_order_item: PayoutOrderItem
) -> InvoiceItem:
	return frappe.get_doc(
		"Invoice Item",
		{
			"parent": invoice_name,
			"document_name": payout_order_item.document_name,
			"document_type": payout_order_item.document_type,
			"plan": payout_order_item.plan,
			"rate": payout_order_item.rate,
		},
	)


@frappe.whitelist()
def create_payout_order_from_invoice_items(
	invoice_items: List[InvoiceItem],
	recipient: str,
	due_date: Optional[str] = "",
	mode_of_payment: str = "Cash",
	notes: str = "",
	type: str = "Marketplace",
	save: bool = True,
) -> PayoutOrder:
	po = frappe.new_doc("Payout Order")
	po.recipient = recipient
	po.due_date = due_date
	po.mode_of_payment = mode_of_payment
	po.notes = notes
	po.type = type

	for invoice_item in invoice_items:
		po.append(
			"items",
			{
				"invoice": invoice_item.parent,
				"document_type": invoice_item.document_type,
				"document_name": invoice_item.document_name,
				"rate": invoice_item.rate,
				"plan": invoice_item.plan,
			},
		)

	if save:
		po.insert()

	return po
