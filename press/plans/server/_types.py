from typing import Any, TypedDict

from frappe.types import DF


class ServerPlanType(TypedDict):
	title: DF.Data
	description: DF.Data
	order_in_list: DF.Int


class ServerPlan(TypedDict):
	name: str
	title: DF.Data | None
	description: DF.Data | None
	enabled: DF.Check
	legacy_plan: DF.Check
	premium: DF.Check
	price_inr: DF.Currency
	price_usd: DF.Currency
	cloud_provider: DF.Link | None
	cluster: DF.Link | None
	instance_type: DF.Data | None
	platform: DF.Literal["x86_64", "arm64", "amd64"]
	vcpu: DF.Int
	memory: DF.Int
	disk: DF.Int
	server_type: DF.Literal["Server", "Database Server", "Proxy Server", "Self Hosted Server"]
	plan_type: ServerPlanType
	allow_unified_server: DF.Check
	ignore_machine_availability_sync: DF.Check
	roles: list[str]

	# fields added to get doc [list] queries at runtime
	machine_unavailable: DF.Check | None
	price_per_day_inr: DF.Float | Any | None
	price_per_day_usd: DF.Float | Any | None


dedicated_instance_type = ServerPlanType(
	title="Dedicated Instance",
	description="Ideal for intense production workloads",
	order_in_list=1,
)
shared_instance_type = ServerPlanType(
	title="Shared Instance",
	description="Ideal for low to medium workloads",
	order_in_list=2,
)
