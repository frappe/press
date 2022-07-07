# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PayoutOrder(Document):
	def validate(self):
		self.validate_items()
		self.validate_net_totals()

	def validate_items(self):
		for row in self.items:
			row.tax = 0
			row.commission = 0
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
			total_transaction_fee = invoice.transaction_fee
			exchange_rate = invoice.exchange_rate

			invoice_item = frappe.get_doc(
				"Invoice Item",
				{
					"parent": invoice_name,
					"document_name": row.document_name,
					"document_type": row.document_type,
					"plan": row.plan,
					"rate": row.rate,
				},
			)

			row.total_amount = invoice_item.amount
			row.currency = invoice.currency

			if transaction_amount > 0:
				if row.currency == "INR":
					row.gateway_fee = (
						total_transaction_fee / transaction_amount
					) * invoice_item.amount
				else:
					if total_transaction_fee == 0 or exchange_rate == 0:
						row.gateway_fee = 0
					else:
						# Converting to USD using gateway exchange rates
						total_transaction_fee = total_transaction_fee / exchange_rate
						transaction_amount = transaction_amount / exchange_rate
						row.gateway_fee = (
							total_transaction_fee / transaction_amount
						) * invoice_item.amount

			else:
				row.gateway_fee = 0

			row.net_amount = row.total_amount - row.tax - row.gateway_fee - row.commission

	def validate_net_totals(self):
		self.net_total_usd = 0
		self.net_total_inr = 0

		for row in self.items:
			if row.currency == "INR":
				self.net_total_inr += row.net_amount
			else:
				self.net_total_usd += row.net_amount
