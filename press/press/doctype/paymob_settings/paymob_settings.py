# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.api.local_payments.paymob.accept_api import AcceptAPI


class PaymobSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Password
		hmac: DF.Password
		iframe: DF.Data
		payment_integration: DF.Int
		public_key: DF.Password
		secret_key: DF.Password
		token: DF.Password | None
	# end: auto-generated types
	
	@frappe.whitelist()
	def get_access_token(self):
		accept = AcceptAPI()
		token = accept.retrieve_auth_token()
		return token
