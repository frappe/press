# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from typing import List

import frappe
from press.press.doctype.site_plan.plan import Plan


class SitePlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF
		from press.press.doctype.site_plan_allowed_app.site_plan_allowed_app import (
			SitePlanAllowedApp,
		)
		from press.press.doctype.site_plan_release_group.site_plan_release_group import (
			SitePlanReleaseGroup,
		)

		allow_downgrading_from_other_plan: DF.Check
		allowed_apps: DF.Table[SitePlanAllowedApp]
		cluster: DF.Link | None
		cpu_time_per_day: DF.Int
		database_access: DF.Check
		dedicated_server_plan: DF.Check
		disk: DF.Int
		document_type: DF.Link
		enabled: DF.Check
		instance_type: DF.Data | None
		interval: DF.Literal["Daily", "Monthly", "Annually"]
		is_frappe_plan: DF.Check
		is_trial_plan: DF.Check
		max_database_usage: DF.Int
		max_storage_usage: DF.Int
		memory: DF.Int
		monitor_access: DF.Check
		offsite_backups: DF.Check
		plan_title: DF.Data | None
		price_inr: DF.Currency
		price_usd: DF.Currency
		private_benches: DF.Check
		release_groups: DF.Table[SitePlanReleaseGroup]
		roles: DF.Table[HasRole]
		support_included: DF.Check
		ten_minutes_scheduler_tick_interval: DF.Check
		thirty_seconds_http_timeout: DF.Check
		vcpu: DF.Int
	# end: auto-generated types

	dashboard_fields = [
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
	]

	def on_update(self):
		for record in self.release_groups:
			rg = frappe.get_doc("Release Group", record.release_group)
			bench_config = []
			if self.thirty_seconds_http_timeout:
				bench_config = [frappe._dict({"key": "http_timeout", "value": 30})]

			deleted_blacklisted_keys = []
			if self.ten_minutes_scheduler_tick_interval:
				common_site_config = rg.merge_common_site_config(
					{"scheduler_tick_interval": 600}, allow_blacklisted_keys=True
				)
			else:
				updated_common_site_config = []
				for row in rg.common_site_config_table:
					if row.key != "scheduler_tick_interval":
						updated_common_site_config.append(
							{"key": row.key, "value": row.value, "type": row.type}
						)
				common_site_config = updated_common_site_config
				deleted_blacklisted_keys.append("scheduler_tick_interval")
			rg.update_config_in_release_group(
				common_site_config,
				bench_config,
				deleted_blacklisted_keys=deleted_blacklisted_keys,
			)
			rg.update_benches_config()

	def get_doc(self, doc):
		doc["price_per_day_inr"] = self.get_price_per_day("INR")
		doc["price_per_day_usd"] = self.get_price_per_day("USD")
		return doc

	@classmethod
	def get_ones_without_offsite_backups(cls) -> List[str]:
		return frappe.get_all("Site Plan", filters={"offsite_backups": False}, pluck="name")


def get_plan_config(name):
	cpu_time = frappe.db.get_value("Site Plan", name, "cpu_time_per_day")
	if cpu_time and cpu_time > 0:
		return {"rate_limit": {"limit": cpu_time * 3600, "window": 86400}}
	return {}
