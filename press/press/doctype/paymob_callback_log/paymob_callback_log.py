# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PaymobCallbackLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event_type: DF.Data | None
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
			paymob_log_name = self.get_paymob_log()
			if paymob_log_name:
				paymob_log_doc = frappe.get_doc("Paymob Log", paymob_log_name)
				self.team = paymob_log_doc.team
				self.payment_partner = paymob_log_doc.payment_partner

	def get_paymob_log(self):
		return frappe.db.get_value("Paymob Log", filters={"special_reference": self.get("special_reference")})

	def after_insert(self):
		# create payment partner log if successed
		if self.payload:
			payload = frappe.parse_json(self.payload)
			if payload.get("obj", {}).get("success"):
				paymob_log = self.get_paymob_log()
				frappe.get_doc({
					"doctype": "Payment Partner Balance Transaction",
					"team": self.team,
					"payment_partner": self.payment_partner,
					"exchange_rate": frappe.db.get_value("Paymob Log", paymob_log, "exchange_rate"),
					"payment_gateway": "Paymob",
					"amount": frappe.db.get_value("Paymob Log", paymob_log, "amount"),
					"actual_amount": frappe.db.get_value("Paymob Log", paymob_log, "actual_amount"),
					"payment_transaction_details": frappe.as_json(frappe.parse_json(self.payload))
				}).insert()


