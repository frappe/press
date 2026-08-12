# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe

from press.press.doctype.site_plan.plan import Plan

# The plan that bills audit log storage. Shipped in press/fixtures/s3_storage_plan.json,
# and the only S3 plan priced per GB of MariaDB Audit Log held in S3.
AUDIT_LOG_STORAGE_PLAN = "Audit Log Storage plan"


class S3StoragePlan(Plan):
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

	dashboard_fields = ("title", "enabled", "price_inr", "price_usd")

	def validate(self):
		if self.enabled and frappe.db.exists("S3 Storage Plan", {"enabled": 1, "name": ("!=", self.name)}):
			frappe.throw(
				"Only one S3 storage plan can be enabled at a time. Please disable the current S3 storage plan before enabling another."
			)
