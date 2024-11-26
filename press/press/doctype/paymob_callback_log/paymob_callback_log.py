# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import parse_json
from frappe import as_json

class PaymobCallbackLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event_type: DF.Data | None
		invoice_id: DF.Data | None
		order_id: DF.Data | None
		payload: DF.Code | None
		payment_partner: DF.Link | None
		special_reference: DF.Data | None
		team: DF.Link | None
		transaction_id: DF.Data | None
	# end: auto-generated types
	def validate(self):
		self.set_missing_data()

	def set_missing_data(self):

		if not self.team or not self.payment_partner:
			paymob_log_data = self._get_paymob_log_data()
			if paymob_log_data:
				self.team, self.payment_partner = paymob_log_data

	def after_insert(self):
		if self._is_payment_successful():
			self._create_payment_partner_transaction()

	def _get_paymob_log_data(self):
		return frappe.db.get_value("Paymob Log", 
			filters={"special_reference": self.special_reference},
			fieldname=["team", "payment_partner"]
		)

	def _is_payment_successful(self) -> bool:

		if not self.payload:
			return False

		try:
			payload = parse_json(self.payload)
			obj = payload.get("obj", {})
			data = obj.get("data", {})

			success = obj.get("success", False)
			is_live = obj.get("is_live", False)

			txn_response_code = data.get("txn_response_code", "")

			return success and is_live and txn_response_code == "APPROVED"
		except ValueError:
			frappe.log_error("PaymobCallbackLog Payload Error", "Invalid JSON format in payload",)
			return False

	def _create_payment_partner_transaction(self):
		try:
			paymob_log_data = frappe.db.get_value(
				"Paymob Log", 
				filters={"special_reference": self.special_reference},
				fieldname=["exchange_rate", "amount", "actual_amount"]
			)
			if not paymob_log_data:
				frappe.log_error(f"Paymob Log not found for reference {self.special_reference}", "PaymobCallbackLog Error")
				return

			exchange_rate, amount, paid_amount = paymob_log_data
			payload=as_json(parse_json(self.payload))
			create_payment_partner_transaction(self.team, self.payment_partner, exchange_rate, amount, paid_amount, "Paymob", payload)


		except Exception as e:
			frappe.log_error("Error creating Payment Partner Transaction", f"PaymobCallbackLog Error :\n{str(e)}")

def create_payment_partner_transaction(team, payment_partner, exchange_rate, amount, paid_amount,payment_gateway, payload=None):
			"""Create a Payment Partner Transaction record."""
			transaction_doc = frappe.get_doc({
				"doctype": "Payment Partner Transaction",
				"team": team,
				"payment_partner": payment_partner,
				"exchange_rate": exchange_rate,
				"payment_gateway": payment_gateway,
				"amount": amount,
				"actual_amount": paid_amount,
				"payment_transaction_details": payload
			})
			transaction_doc.insert()
			transaction_doc.submit()
