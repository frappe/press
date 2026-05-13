from typing import TypedDict

from frappe.types import DF


class SitePlan(TypedDict):
	name: str
	allow_downgrading_from_other_plan: DF.Check
	allowed_apps: DF.Table[str]  # DocType `App`
	cloud_providers: DF.Table[str]  # DocType `Cloud Provider`
	cluster: DF.Link | None
	cpu_time_per_day: DF.Float
	custom_hide_from_pricing_page: DF.Check | None
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
	minimum_server_price_usd: DF.Currency
	monitor_access: DF.Check
	offsite_backups: DF.Check
	plan_description: DF.Data | None
	plan_title: DF.Data | None
	price_inr: DF.Currency
	price_usd: DF.Currency
	private_bench_support: DF.Check
	private_benches: DF.Check
	release_groups: DF.Table[str]  # DocType `Release Group`
	restrict_based_on_dedicated_server_plan: DF.Check
	roles: DF.Table[str]  # DocType `Role`
	support_included: DF.Check
	vcpu: DF.Int
