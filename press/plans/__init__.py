from collections.abc import Callable
from typing import TypeAlias

import frappe
from frappe.utils.data import rounded

from press.plans.server._types import ServerPlan
from press.plans.site._types import SitePlan

AnyPlan: TypeAlias = SitePlan | ServerPlan
FilterFn: TypeAlias = Callable[[AnyPlan], bool]


def _get_price_per_day(plan: AnyPlan, currency):
	price = plan["price_inr"] if currency == "INR" else plan["price_usd"]
	period = frappe.utils.get_last_day(None).day
	return rounded(price / period, 2)


def _get_price_for_interval(plan: AnyPlan, interval, currency):
	price_per_day = _get_price_per_day(plan, currency)

	if interval == "Daily":
		return price_per_day

	if interval == "Monthly":
		return rounded(price_per_day * 30)

	return None


def _is_server_plan_unavailable(plan: str) -> bool:
	result = frappe.db.get_value("Server Plan Unavailability", {"server_plan": plan}, "unavailable")
	return bool(result)


def _get_unavailable_server_plans() -> dict[str, bool]:
	docs = frappe.get_all("Server Plan Unavailability", fields=["server_plan", "unavailable"])
	return {doc["server_plan"]: bool(doc["unavailable"]) for doc in docs}


def _mark_server_plan_as_unavailable(plan: str):
	name = frappe.db.get_value("Server Plan Unavailability", {"server_plan": plan}, "name")
	if name:
		frappe.db.set_value("Server Plan Unavailability", name, "unavailable", 1)
	else:
		frappe.get_doc(
			{
				"doctype": "Server Plan Unavailability",
				"server_plan": plan,
				"unavailable": 1,
			}
		).insert()


def _filter_by_roles(plans):
	out = []
	for plan in plans:
		if frappe.utils.has_common(plan["roles"], frappe.get_roles()):
			plan.pop("roles", "")
			out.append(plan)

	return out
