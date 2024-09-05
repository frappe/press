# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt


from json import dumps, loads

import frappe
from frappe import _
from frappe.model.document import Document

class MpesaSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_balance: DF.LongText | None
		api_type: DF.Literal["", "Mpesa Express", "Mpesa C2B"]
		business_shortcode: DF.Data | None
		consumer_key: DF.Data
		consumer_secret: DF.Password
		initiator_name: DF.Data | None
		online_passkey: DF.Password
		payment_gateway_name: DF.Data
		sandbox: DF.Check
		security_credential: DF.SmallText | None
		team: DF.Link
		till_number: DF.Data
		transaction_limit: DF.Float
	# end: auto-generated types
	supported_currencies = ["KES"]

	