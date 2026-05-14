from collections.abc import Callable
from copy import deepcopy
from typing import Final, TypeAlias

from press.plans import (
	_filter_by_roles,
	_get_price_per_day,
)
from press.plans.site._types import SitePlan
from press.plans.site.plans import _site_plans

FilterFn: TypeAlias = Callable[[SitePlan], bool]

site_plans: Final[list[SitePlan]] = [*_site_plans]


def get_site_plan_list(
	filter_fn: FilterFn | None = None,
	fields: list[str] | None = None,  # TODO: enforce enabled?
) -> list[SitePlan]:
	plans = deepcopy(_site_plans) if filter_fn is None else deepcopy(list(filter(filter_fn, site_plans)))

	role_filtered_plans: list[SitePlan] = _filter_by_roles(plans)

	if fields is None:
		return role_filtered_plans

	return [{k: v for k, v in plan.items() if k in fields} for plan in role_filtered_plans]


def get_site_plan_doc(
	filter_fn: FilterFn | None = None,
	fields: list[str] | None = None,  # TODO: enforce enabled?
) -> SitePlan | None:
	plans = _site_plans if filter_fn is None else list(filter(filter_fn, _site_plans))
	role_filtered_plans: list[SitePlan] = _filter_by_roles(plans)

	if not role_filtered_plans:
		return None

	doc = deepcopy(role_filtered_plans[0])

	doc["price_per_day_inr"] = _get_price_per_day(doc, "INR")
	doc["price_per_day_usd"] = _get_price_per_day(doc, "USD")

	if fields is None:
		return doc

	return {k: v for k, v in doc.items() if k in fields}


def get_site_plans_without_offsite_backups() -> list[SitePlan]:
	return [
		plan["name"]
		for plan in get_site_plan_list(filter_fn=lambda plan: not plan["offsite_backups"], fields=["name"])
	]


def get_site_plan_config(name: str):
	limits = get_site_plan_doc(
		filter_fn=lambda plan: plan["name"] == name,
		fields=["cpu_time_per_day", "max_database_usage", "max_storage_usage"],
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
