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
		roles: DF.Table[HasRole]
		support_included: DF.Check
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
