# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe

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
