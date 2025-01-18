# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class MpesaSetup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_type: DF.Literal["Mpesa Express", "Mpesa C2B"]
		business_shortcode: DF.Data | None
		consumer_key: DF.Data | None
		consumer_secret: DF.Password | None
		initiator_name: DF.Data | None
		passkey: DF.Password | None
		payment_gateway_name: DF.Data | None
		sandbox: DF.Check
		secret_credentials: DF.SmallText | None
		team: DF.Link | None
		till_number: DF.Data | None
		transaction_limit: DF.Float
	# end: auto-generated types

	pass
