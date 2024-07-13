# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.site_plan.plan import Plan


class ServerStoragePlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		price_inr: DF.Currency
		price_usd: DF.Currency
		title: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if self.enabled and frappe.db.exists(
			"Server Storage Plan", {"enabled": 1, "name": ("!=", self.name)}
		):
			frappe.throw("Only one storage add-on plan can be enabled at a time")
