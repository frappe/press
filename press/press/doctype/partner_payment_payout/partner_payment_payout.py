# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PartnerPaymentPayout(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.partner_payment_payout_item.partner_payment_payout_item import (
			PartnerPaymentPayoutItem,
		)

		amended_from: DF.Link | None
		commission: DF.Currency
		from_date: DF.Date | None
		net_amount: DF.Currency
		partner: DF.Link
		partner_commission: DF.Percent
		payment_gateway: DF.Link
		posting_date: DF.Date | None
		to_date: DF.Date | None
		total_amount: DF.Currency
		transfer_items: DF.Table[PartnerPaymentPayoutItem]
	# end: auto-generated types
	dashboard_fields = (
		"posting_date",
		"total_amount",
		"commission",
		"net_amount",
		"payment_gateway",
	)

	def before_save(self):
		self.total_amount = sum([item.amount for item in self.transfer_items])
		self.commission = self.total_amount * (self.partner_commission / 100)
		self.net_amount = self.total_amount - self.commission
		for item in self.transfer_items:
			item.commission_amount = item.amount * (self.partner_commission / 100)
			item.net_amount = item.amount - item.commission_amount

	def on_submit(self):
		transaction_names = [item.transaction_id for item in self.transfer_items]

		if transaction_names:
			frappe.db.set_value(
				"Payment Partner Transaction",
				{"name": ["in", transaction_names], "submitted_to_frappe": 0},
				"submitted_to_frappe",
				1,
			)
			frappe.db.commit()

	def on_cancel(self):
		transaction_names = [item.transaction_id for item in self.transfer_items]

		# Update Payment Partner Records
		if transaction_names:
			frappe.db.set_value(
				"Payment Partner Transaction",
				{"name": ["in", transaction_names], "submitted_to_frappe": 1},
				"submitted_to_frappe",
				0,
			)
			frappe.db.commit()


@frappe.whitelist()
def submit_payment_payout(partner, payment_gateway, from_date, to_date, partner_commission, transactions):
	partner = (
		partner if frappe.db.exists("Team", partner) else frappe.get_value("Team", {"user": partner}, "name")
	)

	try:
		payout = frappe.new_doc("Partner Payment Payout")
		payout.partner = partner
		payout.payment_gateway = payment_gateway
		payout.from_date = from_date
		payout.to_date = to_date
		payout.partner_commission = partner_commission

		for transaction in transactions:
			payout.append(
				"transfer_items",
				{
					"transaction_id": transaction.get("name"),
					"amount": transaction.get("amount"),
					"posting_date": transaction.get("posting_date"),
				},
			)

		payout.total_amount = sum(t.get("amount", 0) for t in transactions)
		payout.commission = payout.total_amount * (payout.partner_commission / 100)
		payout.net_amount = payout.total_amount - payout.commission

		payout.insert()
		payout.submit()

		transaction_names = [t.get("name") for t in transactions]
		if transaction_names:
			frappe.db.set_value(
				"Payment Partner Transaction",
				{"name": ["in", transaction_names], "submitted_to_frappe": 0},
				"submitted_to_frappe",
				1,
			)

		return {
			"name": payout.name,
			"total_amount": payout.total_amount,
			"commission": payout.commission,
			"net_amount": payout.net_amount,
		}

	except Exception as e:
		frappe.log_error(f"Failed to create payout: {e!s}")
