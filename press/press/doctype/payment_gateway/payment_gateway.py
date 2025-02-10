# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PaymentGateway(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Data | None
		api_secret: DF.Password | None
		currency: DF.Link | None
		gateway: DF.Data | None
		gateway_controller: DF.DynamicLink | None
		gateway_settings: DF.Link | None
		integration_logo: DF.AttachImage | None
		print_format: DF.Data | None
		taxes_and_charges: DF.Percent
		team: DF.Link | None
		team_name: DF.Data | None
		url: DF.Data | None
	# end: auto-generated types

	pass
