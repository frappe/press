# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe

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
		legacy_plan: DF.Check
		memory: DF.Int
		platform: DF.Literal["x86_64", "arm64", "amd64"]
		premium: DF.Check
		price_inr: DF.Currency
		price_usd: DF.Currency
		roles: DF.Table[HasRole]
		server_type: DF.Literal["Server", "Database Server", "Proxy Server", "Self Hosted Server"]
		title: DF.Data | None
		vcpu: DF.Int
	# end: auto-generated types

	dashboard_fields = (
		"title",
		"price_inr",
		"price_usd",
		"vcpu",
		"memory",
		"disk",
		"platform",
		"premium",
	)

	def get_doc(self, doc):
		doc["price_per_day_inr"] = self.get_price_per_day("INR")
		doc["price_per_day_usd"] = self.get_price_per_day("USD")
		return doc

	def validate(self):
		self.validate_active_subscriptions()

	def validate_active_subscriptions(self):
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.enabled and not self.enabled:
			active_sub_count = frappe.db.count("Subscription", {"enabled": 1, "plan": self.name})
			if active_sub_count > 0:
				frappe.throw(
					f"Cannot disable this plan. This plan is used in {active_sub_count} active subscription(s)."
				)
