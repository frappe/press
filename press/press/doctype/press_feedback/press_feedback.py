# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PressFeedback(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		currency: DF.Link | None
		last_paid_invoice: DF.Currency
		message: DF.Data
		note: DF.SmallText | None
		rating: DF.Rating
		route: DF.Data | None
		team: DF.Link
		team_created_on: DF.Date | None
	# end: auto-generated types

	pass
