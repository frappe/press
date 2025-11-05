# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from press.press.doctype.site_plan.plan import Plan


class ServerSnapshotPlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		price_inr: DF.Currency
		price_usd: DF.Currency
		provider: DF.Literal["AWS EC2"]
		title: DF.Data | None
	# end: auto-generated types

	pass
