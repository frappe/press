# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PartnerPaymentPayout(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.partner_payment_payout_item.partner_payment_payout_item import PartnerPaymentPayoutItem

		amended_from: DF.Link | None
		commission: DF.Currency
		from_date: DF.Date | None
		net_amount: DF.Currency
		partner: DF.Link
		partner_commission: DF.Percent
		payment_gateway: DF.Link
		to_date: DF.Date | None
		total_amount: DF.Currency
		transfer_items: DF.Table[PartnerPaymentPayoutItem]
	# end: auto-generated types
	pass

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
				1
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
				0
			)
			frappe.db.commit()
	  

@frappe.whitelist(allow_guest=True)
def fetch_payments():
	payment_gateway = frappe.form_dict.get('payment_gateway')
	partner = frappe.form_dict.get('partner')
	from_date = frappe.form_dict.get('from_date')
	to_date = frappe.form_dict.get('to_date')

	filters = {
		'docstatus': 1,
		'submitted_to_frappe': 0,
		'payment_gateway': payment_gateway,
		'payment_partner': partner
	}

	if from_date and to_date:
		filters['posting_date'] = ['between', [from_date, to_date]]


	partner_payments = frappe.get_all(
		"Payment Partner Transaction",
		filters=filters,
		fields=['name', 'amount', 'posting_date']
	)

	frappe.response.message = partner_payments
	
