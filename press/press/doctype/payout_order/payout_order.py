# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe

from itertools import groupby
from typing import List
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
				[
					"status",
					"currency",
					"transaction_fee",
					"exchange_rate",
					"amount_paid",
				],
				as_dict=True,
			)

			if invoice.status != "Paid":
				frappe.throw(f"Invoice {invoice_name} is not paid yet.")

			invoice_item = get_invoice_item_for_po_item(invoice_name, row)

			row.tax = row.tax or 0.0
			row.commission = row.commission or 0.0
			row.total_amount = invoice_item.amount
			row.site = invoice_item.site
			row.currency = invoice.currency
			row.gateway_fee = 0.0

			if invoice.transaction_fee > 0:
				row.gateway_fee = (invoice.transaction_fee) * (
					invoice_item.amount / invoice.amount_paid
				)
				if invoice.exchange_rate > 0:
					row.gateway_fee = row.gateway_fee / invoice.exchange_rate

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


def create_marketplace_payout_orders_monthly():
	today = frappe.utils.today()
	period_start = frappe.utils.data.get_first_day(today)
	period_end = frappe.utils.data.get_last_day(today)

	# Get all marketplace app invoice items
	invoice = frappe.qb.DocType("Invoice")
	invoice_item = frappe.qb.DocType("Invoice Item")
	marketplace_app = frappe.qb.DocType("Marketplace App")

	items = (
		frappe.qb.from_(invoice_item)
		.left_join(invoice)
		.on(invoice_item.parent == invoice.name)
		.left_join(marketplace_app)
		.on(marketplace_app.name == invoice_item.document_name)
		.where(invoice.status == "Paid")
		.where(invoice_item.document_type == "Marketplace App")
		.where(invoice_item.has_marketplace_payout_completed == 0)
		.select(
			invoice_item.name, invoice_item.document_name, marketplace_app.team.as_("app_team")
		)
		.run(as_dict=True)
	)

	# Group by teams
	for app_team, items in groupby(items, key=lambda x: x["app_team"]):
		item_names = [i.name for i in items]

		po_exists = frappe.db.exists(
			"Payout Order", {"recipient": app_team, "period_end": period_end}
		)

		if not po_exists:
			create_payout_order_from_invoice_item_names(
				item_names, recipient=app_team, period_start=period_start, period_end=period_end
			)
		else:
			po = frappe.get_doc(
				"Payout Order", {"recipient": app_team, "period_end": period_end}
			)
			for item_name in item_names:
				invoice_item = frappe.get_doc("Invoice Item", item_name)
				po.append(
					"items",
					{
						"invoice_item": invoice_item.name,
						"invoice": invoice_item.parent,
						"document_type": invoice_item.document_type,
						"document_name": invoice_item.document_name,
						"rate": invoice_item.rate,
						"plan": invoice_item.plan,
						"quantity": invoice_item.quantity,
						"site": invoice_item.site,
					},
				)
			po.save()

		frappe.db.set_value(
			"Invoice Item",
			{"name": ("in", item_names)},
			"has_marketplace_payout_completed",
			True,
		)


@frappe.whitelist()
def create_payout_order_from_invoice_items(
	invoice_items: List[InvoiceItem],
	recipient: str,
	period_start: str,
	period_end: str,
	mode_of_payment: str = "Cash",
	notes: str = "",
	type: str = "Marketplace",
	save: bool = True,
) -> PayoutOrder:
	po = frappe.get_doc(
		{
			"doctype": "Payout Order",
			"recipient": recipient,
			"mode_of_payment": mode_of_payment,
			"notes": notes,
			"type": type,
			"period_start": period_start,
			"period_end": period_end,
		}
	)

	for invoice_item in invoice_items:
		po.append(
			"items",
			{
				"invoice_item": invoice_item.name,
				"invoice": invoice_item.parent,
				"document_type": invoice_item.document_type,
				"document_name": invoice_item.document_name,
				"rate": invoice_item.rate,
				"plan": invoice_item.plan,
				"quantity": invoice_item.quantity,
				"site": invoice_item.site,
			},
		)

	if save:
		po.insert()

	return po


def create_payout_order_from_invoice_item_names(item_names, *args, **kwargs):
	invoice_items = (frappe.get_doc("Invoice Item", i) for i in item_names)
	return create_payout_order_from_invoice_items(invoice_items, *args, **kwargs)
