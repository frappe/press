# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PressWebhookEvent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.Data
		enabled: DF.Check
		title: DF.Data
	# end: auto-generated types

	DOCTYPE = "Press Webhook Event"
	dashboard_fields = ("name", "description")
