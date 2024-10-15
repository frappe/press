# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PaymobLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		event_type: DF.Data | None
		payload: DF.Code | None
		payment_partner: DF.Link | None
		special_reference: DF.Data | None
		team: DF.Link | None
	# end: auto-generated types
	pass
