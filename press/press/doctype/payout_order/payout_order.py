# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from datetime import date
from itertools import groupby
from typing import List

import frappe
from frappe.model.document import Document

from press.press.doctype.invoice_item.invoice_item import InvoiceItem
from press.press.doctype.payout_order_item.payout_order_item import PayoutOrderItem
from press.utils import log_error


class PayoutOrder(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.payout_order_item.payout_order_item import PayoutOrderItem

		amended_from: DF.Link | None
		currency_inr: DF.Data | None
		currency_usd: DF.Data | None
		due_date: DF.Date | None
		frappe_purchase_order: DF.Data | None
		ignore_commission: DF.Check
		items: DF.Table[PayoutOrderItem]
		mode_of_payment: DF.Literal["Cash", "Credits", "Internal"]
		net_total_inr: DF.Currency
		net_total_usd: DF.Currency
		notes: DF.SmallText | None
		period_end: DF.Date | None
		period_start: DF.Date | None
		recipient_currency: DF.Data | None
		status: DF.Literal["Draft", "Paid", "Commissioned"]
		team: DF.Link
		total_amount: DF.Currency
		type: DF.Literal["Marketplace", "SaaS"]
	# end: auto-generated types

	dashboard_fields = [
		"period_end",
		"team",
		"mode_of_payment",
		"net_total_inr",
		"net_total_usd",
		"status",
		"total_amount",
		"items",
	]

	@staticmethod
	def get_list_query(query):
		PayoutOrder = frappe.qb.DocType("Payout Order")
		query = query.where((PayoutOrder.docstatus != 2))
		return query

	def validate(self):
		self.validate_items()
		self.validate_net_totals()
		self.compute_total_amount()

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

			# check to avoid app revenue ledger item's calculation
			if not invoice_item:
				return

			row.tax = row.tax or 0.0
			row.total_amount = invoice_item.amount
			row.site = invoice_item.site
			row.currency = invoice.currency
			row.gateway_fee = 0.0

			# validate commissions and thresholds
			app_payment = (
				frappe.get_cached_doc("Marketplace App Payment", row.document_name)
				if frappe.db.exists("Marketplace App Payment", row.document_name)
				else frappe.get_doc(
					{
						"doctype": "Marketplace App Payment",
						"app": row.document_name,
						"team": self.team,
					}
				).insert(ignore_permissions=True)
			)

			row.commission = (
				app_payment.get_commission(row.total_amount) if not self.ignore_commission else 0.0
			)

			row.net_amount = row.total_amount - row.commission

			if row.currency == "INR":
				app_payment.total_inr += row.net_amount if row.net_amount > 0 else row.commission
			else:
				app_payment.total_usd += row.net_amount if row.net_amount > 0 else row.commission

			app_payment.save(ignore_permissions=True)

	def validate_net_totals(self):
		self.net_total_usd = 0
		self.net_total_inr = 0

		for row in self.items:
			if row.currency == "INR":
				self.net_total_inr += row.net_amount
			else:
				self.net_total_usd += row.net_amount

		if self.net_total_usd <= 0 and self.net_total_inr <= 0:
			self.status = "Commissioned"
		elif (self.net_total_usd > 0 or self.net_total_inr > 0) and not self.frappe_purchase_order:
			self.status = "Draft"

	def compute_total_amount(self):
		exchange_rate = frappe.db.get_single_value("Press Settings", "usd_rate")
		if self.recipient_currency == "USD":
			inr_in_usd = 0
			if self.net_total_inr > 0:
				inr_in_usd = self.net_total_inr / exchange_rate
			self.total_amount = self.net_total_usd + inr_in_usd
		elif self.recipient_currency == "INR":
			self.total_amount = self.net_total_inr + (self.net_total_usd * exchange_rate)

	def before_submit(self):
		if self.mode_of_payment == "Cash" and (not self.frappe_purchase_order):
			frappe.throw(
				"Frappe Purchase Order is required before marking this cash payout as Paid"
			)
		self.status = "Paid"


def get_invoice_item_for_po_item(
	invoice_name: str, payout_order_item: PayoutOrderItem
) -> InvoiceItem | None:
	try:
		if payout_order_item.invoice_item:
			item = frappe.get_doc("Invoice Item", payout_order_item.invoice_item)
			if (
				item.parent == invoice_name
				and item.document_name == payout_order_item.document_name
				and item.document_type == payout_order_item.document_type
				and item.plan == payout_order_item.plan
				and item.rate == payout_order_item.rate
			):
				return item

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
	except frappe.DoesNotExistError:
		return None


def create_marketplace_payout_orders_monthly(period_start=None, period_end=None):
	period_start, period_end = (
		(period_start, period_end)
		if period_start and period_end
		else get_current_period_boundaries()
	)
	items = get_unaccounted_marketplace_invoice_items()

	# Group by teams
	for app_team, items in groupby(items, key=lambda x: x["app_team"]):
		try:
			item_names = [i.name for i in items]

			po_exists = frappe.db.exists(
				"Payout Order", {"team": app_team, "period_end": period_end}
			)

			if not po_exists:
				create_payout_order_from_invoice_item_names(
					item_names, team=app_team, period_start=period_start, period_end=period_end
				)
			else:
				po = frappe.get_doc("Payout Order", {"team": app_team, "period_end": period_end})
				add_invoice_items_to_po(po, item_names)

			frappe.db.set_value(
				"Invoice Item",
				{"name": ("in", item_names)},
				"has_marketplace_payout_completed",
				True,
			)

			if not frappe.flags.in_test:
				# Save this particular PO transaction
				frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error("Payout Order Creation Error", team=app_team, invoice_items=items)


def get_current_period_boundaries():
	today = frappe.utils.today()
	period_start = frappe.utils.data.get_first_day(today)
	period_end = frappe.utils.data.get_last_day(today)

	return period_start, period_end


def add_invoice_items_to_po(po, invoice_item_names):
	for item_name in invoice_item_names:
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


def get_unaccounted_marketplace_invoice_items():
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
		.distinct()
		.run(as_dict=True)
	)

	return items


@frappe.whitelist()
def create_payout_order_from_invoice_items(
	invoice_items: List[InvoiceItem],
	team: str,
	period_start: date,
	period_end: date,
	mode_of_payment: str = "Cash",
	notes: str = "",
	type: str = "Marketplace",
	save: bool = True,
) -> PayoutOrder:
	po = frappe.get_doc(
		{
			"doctype": "Payout Order",
			"team": team,
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


def create_marketplace_payout_orders():
	# ONLY RUN ON LAST DAY OF THE MONTH
	today = frappe.utils.today()
	period_end = frappe.utils.data.get_last_day(today).strftime("%Y-%m-%d")

	if today != period_end:
		return

	create_marketplace_payout_orders_monthly()
