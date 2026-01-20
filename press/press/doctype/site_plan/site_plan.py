# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe

from press.press.doctype.site_plan.plan import Plan

UNLIMITED_PLANS = ["Unlimited", "Unlimited - Supported"]


class SitePlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		from press.press.doctype.site_plan_allowed_app.site_plan_allowed_app import SitePlanAllowedApp
		from press.press.doctype.site_plan_release_group.site_plan_release_group import SitePlanReleaseGroup

		allow_downgrading_from_other_plan: DF.Check
		allowed_apps: DF.Table[SitePlanAllowedApp]
		cloud_providers: DF.Table[CloudProviders]
		cluster: DF.Link | None
		cpu_time_per_day: DF.Float
		database_access: DF.Check
		dedicated_server_plan: DF.Check
		disk: DF.Int
		document_type: DF.Link
		enabled: DF.Check
		instance_type: DF.Data | None
		interval: DF.Literal["Daily", "Monthly", "Annually"]
		is_frappe_plan: DF.Check
		is_trial_plan: DF.Check
		legacy_plan: DF.Check
		max_database_usage: DF.Int
		max_storage_usage: DF.Int
		memory: DF.Int
		monitor_access: DF.Check
		offsite_backups: DF.Check
		plan_title: DF.Data | None
		price_inr: DF.Currency
		price_usd: DF.Currency
		private_bench_support: DF.Check
		private_benches: DF.Check
		release_groups: DF.Table[SitePlanReleaseGroup]
		roles: DF.Table[HasRole]
		support_included: DF.Check
		vcpu: DF.Int
	# end: auto-generated types

	dashboard_fields = (
		"name",
		"plan_title",
		"document_type",
		"document_name",
		"price_inr",
		"price_usd",
		"period",
		"cpu_time_per_day",
		"max_database_usage",
		"max_storage_usage",
		"database_access",
		"support_included",
		"private_benches",
		"monitor_access",
		"is_trial_plan",
	)

	def get_doc(self, doc):
		doc["price_per_day_inr"] = self.get_price_per_day("INR")
		doc["price_per_day_usd"] = self.get_price_per_day("USD")
		return doc

	@classmethod
	def get_ones_without_offsite_backups(cls) -> list[str]:
		return frappe.get_all("Site Plan", filters={"offsite_backups": False}, pluck="name")

	def validate(self):
		self.validate_active_subscriptions()

	def validate_active_subscriptions(self):
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.enabled and not self.enabled and not self.legacy_plan:
			active_sub_count = frappe.db.count("Subscription", {"enabled": 1, "plan": self.name})
			if active_sub_count > 0:
				frappe.throw(
					f"Cannot disable this plan. This plan is used in {active_sub_count} active subscription(s)."
				)


def get_plan_config(name):
	limits = frappe.db.get_value(
		"Site Plan",
		name,
		["cpu_time_per_day", "max_database_usage", "max_storage_usage"],
		as_dict=True,
	)
	if limits and limits.get("cpu_time_per_day", 0) > 0:
		return {
			"rate_limit": {"limit": limits.cpu_time_per_day * 3600, "window": 86400},
			"plan_limit": {
				"max_database_usage": limits.max_database_usage,
				"max_storage_usage": limits.max_storage_usage,
			},
		}
	return {}
