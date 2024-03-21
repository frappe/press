# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from press.press.doctype.site_plan.plan import Plan


class ClusterPlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		enabled: DF.Check
		price_inr: DF.Currency
		price_usd: DF.Currency
		roles: DF.Table[HasRole]
		title: DF.Data | None
	# end: auto-generated types

	pass
