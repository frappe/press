# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from press.press.doctype.site_plan.plan import Plan


class ServerPlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		cluster: DF.Link | None
		disk: DF.Int
		enabled: DF.Check
		instance_type: DF.Data | None
		memory: DF.Int
		price_inr: DF.Currency
		price_usd: DF.Currency
		roles: DF.Table[HasRole]
		server_type: DF.Literal[
			"Server", "Database Server", "Proxy Server", "Self Hosted Server"
		]
		title: DF.Data | None
		vcpu: DF.Int
	# end: auto-generated types

	dashboard_fields = [
		"title",
		"price_inr",
		"price_usd",
		"vcpu",
		"memory",
		"disk",
	]

	def get_doc(self, doc):
		doc["price_per_day_inr"] = self.get_price_per_day("INR")
		doc["price_per_day_usd"] = self.get_price_per_day("USD")
		return doc
