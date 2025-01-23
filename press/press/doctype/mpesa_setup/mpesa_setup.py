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
		consumer_key: DF.Data
		consumer_secret: DF.Password
		initiator_name: DF.Data | None
		mpesa_setup_id: DF.Data
		pass_key: DF.Password
		sandbox: DF.Check
		security_credential: DF.SmallText
		team: DF.Link
		till_number: DF.Data
		transaction_limit: DF.Float
	# end: auto-generated types

	pass
