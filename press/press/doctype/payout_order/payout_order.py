# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

from datetime import date
from itertools import groupby
from typing import ClassVar

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
		commission: DF.Currency
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
		status: DF.Literal["Draft", "Unpaid", "Paid", "Commissioned", "Submitted"]
		team: DF.Link
		total_amount: DF.Currency
		type: DF.Literal["Marketplace", "SaaS"]
	# end: auto-generated types

	dashboard_fields: ClassVar = [
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
		return query.where(PayoutOrder.docstatus != 2)

	def validate(self):
		for row in self.items:
			if row.currency == "INR":
				self.net_total_inr += row.net_amount
			elif row.currency == "USD":
				self.net_total_usd += row.net_amount

	def on_update(self):
		if self.docstatus != 1:
			return
		if self.mode_of_payment == "Cash" and self.status == "Paid" and not self.frappe_purchase_order:
			frappe.throw("Frappe Purchase Order is required before marking this cash payout as Paid")

	def before_submit(self):
		self.set_total_and_track_revenue_in_marketplace_app_payment()
		self.compute_total_amount_payable()

	def on_submit(self):
		self.set_status()

	def set_total_and_track_revenue_in_marketplace_app_payment(self):
		"""
		- Verify payout order items with respective invoices
		- Calculate row-wise commission and net amounts
		- Update totals in Marketplace App Payment docs
		- Calculate total commission and net totals
		"""
		self.net_total_inr = 0.0
		self.net_total_usd = 0.0
		total_commission = 0.0

		for row in self.items:
			invoice = self._get_invoice_data(row.invoice)
			invoice_item = get_invoice_item_for_po_item(row.invoice, row)

			# check to avoid app revenue ledger item's calculation
			if not invoice_item:
				self._update_net_totals(row)
				continue

			self._populate_row_data(row, invoice_item, invoice)

			app_payment = self._get_or_create_app_payment(row.document_name)

			# Calculate commission based on current Marketplace App Payment totals
			row.commission = self._calculate_commission(app_payment, row.total_amount, row.currency)
			row.net_amount = row.total_amount - row.commission

			self._update_app_payment_record(app_payment, row)

			self._update_net_totals(row)
			total_commission += self._convert_commission_to_recipient_currency(row.commission, row.currency)

		if self.type == "Marketplace":
			self.commission = total_commission

	def _get_invoice_data(self, invoice_name):
		invoice = frappe.db.get_value("Invoice", invoice_name, ["status", "currency"], as_dict=True)
		if not invoice:
			frappe.throw(f"Invoice {invoice_name} not found")
		if invoice.status != "Paid":
			frappe.throw(f"Invoice {invoice_name} is not paid yet")
		return invoice

	def _populate_row_data(self, row, invoice_item, invoice):
		row.tax = row.tax or 0.0
		row.total_amount = invoice_item.amount
		row.site = invoice_item.site
		row.currency = invoice.currency
		row.gateway_fee = 0.0

	def _get_or_create_app_payment(self, app_name):
		if frappe.db.exists("Marketplace App Payment", app_name):
			return frappe.get_doc("Marketplace App Payment", app_name)

		app_payment = frappe.get_doc(
			{
				"doctype": "Marketplace App Payment",
				"app": app_name,
				"team": self.team,
			}
		)
		app_payment.insert(ignore_permissions=True)
		return app_payment

	def _calculate_commission(self, app_payment, total_amount, currency):
		if self.ignore_commission:
			return 0.0
		return app_payment.get_commission(total_amount, currency)

	def _update_net_totals(self, row):
		if row.currency == "INR":
			self.net_total_inr += row.net_amount
		elif row.currency == "USD":
			self.net_total_usd += row.net_amount

	def _convert_commission_to_recipient_currency(self, commission, row_currency):
		exchange_rate = frappe.db.get_single_value("Press Settings", "usd_rate") or 80

		if row_currency == self.recipient_currency:
			return commission
		if self.recipient_currency == "INR" and row_currency == "USD":
			return commission * exchange_rate
		if self.recipient_currency == "USD" and row_currency == "INR":
			return commission / exchange_rate
		return 0

	def _update_app_payment_record(self, app_payment, row):
		if row.currency == "INR":
			app_payment.total_inr = (app_payment.total_inr or 0) + row.total_amount
			app_payment.commission_inr = (app_payment.commission_inr or 0) + row.commission
		elif row.currency == "USD":
			app_payment.total_usd = (app_payment.total_usd or 0) + row.total_amount
			app_payment.commission_usd = (app_payment.commission_usd or 0) + row.commission

		app_payment.save(ignore_permissions=True)

	def compute_total_amount_payable(self):
		exchange_rate = frappe.db.get_single_value("Press Settings", "usd_rate")
		if self.recipient_currency == "USD":
			inr_in_usd = 0
			if self.net_total_inr > 0:
				inr_in_usd = self.net_total_inr / exchange_rate
			self.total_amount = self.net_total_usd + inr_in_usd
		elif self.recipient_currency == "INR":
			self.total_amount = self.net_total_inr + (self.net_total_usd * exchange_rate)

	def set_status(self):
		if self.docstatus != 1:
			return

		if self.total_amount > 0:
			status = "Unpaid"
		elif self.commission > 0:
			status = "Commissioned"
		else:
			status = "Submitted"

		self.db_set("status", status)


def get_invoice_item_for_po_item(invoice_name: str, payout_order_item: PayoutOrderItem) -> InvoiceItem | None:
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
		(period_start, period_end) if period_start and period_end else get_current_period_boundaries()
	)
	invoice_items = get_unaccounted_marketplace_invoice_items()

	# Group by teams
	for app_team, team_items in groupby(invoice_items, key=lambda x: x["app_team"]):
		try:
			team_items = list(team_items)
			item_names = [i.name for i in team_items]

			po_exists = frappe.db.exists(
				"Payout Order", {"team": app_team, "period_end": period_end, "docstatus": 0}
			)

			if not po_exists:
				po = create_payout_order_from_invoice_item_names(
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
			po.submit()

			if not frappe.flags.in_test:
				# Save this particular PO transaction
				frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			log_error("Payout Order Creation Error", team=app_team, invoice_items=team_items)

	send_unpaid_payout_order_notification()


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

	return (
		frappe.qb.from_(invoice_item)
		.left_join(invoice)
		.on(invoice_item.parent == invoice.name)
		.left_join(marketplace_app)
		.on(marketplace_app.name == invoice_item.document_name)
		.where(invoice.status == "Paid")
		.where(invoice_item.document_type == "Marketplace App")
		.where(invoice_item.has_marketplace_payout_completed == 0)
		.select(invoice_item.name, invoice_item.document_name, marketplace_app.team.as_("app_team"))
		.distinct()
		.run(as_dict=True)
	)


@frappe.whitelist()
def create_payout_order_from_invoice_items(
	invoice_items: list[InvoiceItem],
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


def send_unpaid_payout_order_notification():
	"""
	Send reminder emails to the configured email address for unpaid Marketplace payout orders.
	"""
	if not frappe.get_single_value("Marketplace Settings", "enable_payout_reminder"):
		return

	email = frappe.get_single_value("Marketplace Settings", "email")

	unpaid_orders = frappe.get_all(
		"Payout Order",
		filters={"status": "Unpaid", "docstatus": 1, "type": "Marketplace"},
		fields=[
			"name",
			"team",
			"period_start",
			"period_end",
			"recipient_currency",
			"total_amount",
		],
	)

	if not unpaid_orders:
		return

	team_details = {}
	for order in unpaid_orders:
		currency = "₹" if order["recipient_currency"] == "INR" else "$"
		order["amount"] = f"{currency}{order['total_amount']}"

		team = order.team
		if team not in team_details:
			team_details[team] = {"id": team, "user": frappe.db.get_value("Team", team, "user")}

	try:
		frappe.sendmail(
			recipients=email,
			subject=f"Marketplace App Payout Reminder: {total_orders} Unpaid Order(s) Pending",
			template="payout_reminder",
			args={
				"total_orders": len(unpaid_orders),
				"payout_orders": unpaid_orders,
				"team_details": team_details,
			},
		)

	except Exception as e:
		frappe.log_error(
			title="Failed to Send Payout Reminder Email",
			message=f"Error sending marketplace payout reminder to {marketplace_settings.email}: {e!s}",
		)


@frappe.whitelist()
def mark_as_paid(payout_order):
	doc = frappe.get_doc("Payout Order", payout_order)

	# Verify document is submitted and unpaid
	if doc.docstatus != 1:
		frappe.throw("Payout Order must be submitted to mark as paid")

	if doc.status != "Unpaid":
		frappe.throw("Payout Order is not in Unpaid status")

	return doc.db_set("status", "Paid", update_modified=True)


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
