from collections.abc import Callable
from copy import deepcopy
from typing import TYPE_CHECKING, Final, TypeAlias, cast

import frappe

from press.plans import (
	_filter_by_roles,
	_get_price_per_day,
	_get_unavailable_server_plans,
	_is_server_plan_unavailable,
	_mark_server_plan_as_unavailable,
)
from press.plans.server._types import ServerPlan
from press.plans.server.aws import _aws_server_plans
from press.plans.server.do import _do_server_plans
from press.plans.server.frappe import _frappe_compute_server_plans
from press.plans.server.hetzner import _hetzner_server_plans
from press.plans.server.oci import _oci_server_plans
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster

FilterFn: TypeAlias = Callable[[ServerPlan], bool]

_server_plans: Final[list[ServerPlan]] = [
	*_aws_server_plans,
	*_frappe_compute_server_plans,
	*_do_server_plans,
	*_oci_server_plans,
	*_hetzner_server_plans,
]


def get_server_plan_list(
	filter_fn: FilterFn | None = None,
	fields: list[str] | None = None,  # TODO: enforce enabled?
) -> list[ServerPlan]:
	plans = deepcopy(_server_plans) if filter_fn is None else deepcopy(list(filter(filter_fn, _server_plans)))

	if fields and "machine_unavailable" in fields:
		unavailable_plans = _get_unavailable_server_plans()
		for plan in plans:
			plan["machine_unavailable"] = unavailable_plans.get(plan["name"], False)

	role_filtered_plans: list[ServerPlan] = _filter_by_roles(plans)

	if fields is None:
		return role_filtered_plans

	return cast(
		"list[ServerPlan]", [{k: v for k, v in plan.items() if k in fields} for plan in role_filtered_plans]
	)


def get_server_plan_doc(
	filter_fn: FilterFn | None = None,
	fields: list[str] | None = None,  # TODO: enforce enabled?
) -> ServerPlan | None:
	plans = _server_plans if filter_fn is None else list(filter(filter_fn, _server_plans))
	role_filtered_plans: list[ServerPlan] = _filter_by_roles(plans)

	if not role_filtered_plans:
		return None

	doc = deepcopy(role_filtered_plans[0])

	doc["price_per_day_inr"] = _get_price_per_day(doc, "INR")
	doc["price_per_day_usd"] = _get_price_per_day(doc, "USD")
	doc["machine_unavailable"] = _is_server_plan_unavailable(doc["name"])

	if fields is None:
		return doc

	return cast("ServerPlan", {k: v for k, v in doc.items() if k in fields})


def sync_machine_availability_status_of_plans():
	frappe.enqueue(
		_sync_machine_availability_status_of_plans,
		timeout=3600,
		deduplicate=True,
		job_id="sync_machine_availability_status_of_plans",
	)


def _sync_machine_availability_status_of_plans():  # noqa
	plans = get_server_plan_list(
		filter_fn=lambda plan: plan["ignore_machine_availability_sync"] == 0 and plan["enabled"],
		fields=["name", "cluster", "machine_unavailable", "instance_type"],
	)

	# Sync also disabled but legacy_plan
	legacy_plans = get_server_plan_list(
		filter_fn=lambda plan: plan["legacy_plan"]
		and not plan["ignore_machine_availability_sync"]
		and not plan["enabled"],
		fields=["name", "cluster", "machine_unavailable", "instance_type"],
	)
	plans.extend(legacy_plans)

	cluster_doc_map: dict[str, Cluster] = {}
	cluster_plans: dict[str, list[dict]] = {}

	for plan in plans:
		if has_job_timeout_exceeded():
			return

		if not plan["instance_type"]:
			continue

		if not plan["cluster"]:
			# Some plan types has no cluster assigned to them.
			# Skip those as they are not relevant for machine availability status sync.
			continue

		if plan["cluster"] not in cluster_doc_map:
			cluster_doc_map[plan["cluster"]] = frappe.get_doc("Cluster", plan["cluster"])

		if plan["cluster"] not in cluster_plans:
			cluster_plans[plan["cluster"]] = []
		cluster_plans[plan["cluster"]].append(plan)

	for c in cluster_plans:
		if has_job_timeout_exceeded():
			return

		try:
			cluster: Cluster = cluster_doc_map[c]
			instance_types = [p["instance_type"] for p in cluster_plans[c]]
			plan_availability_results = cluster.check_machine_availability(instance_types)

			# Some Cluster implementations may return a boolean instead of a dict.
			# Normalize to a dict so that the code below can safely use .get(...).
			if isinstance(plan_availability_results, bool):
				plan_availability_results = {
					instance_type: plan_availability_results for instance_type in instance_types
				}
			for plan in cluster_plans[c]:
				is_unavailable = not plan_availability_results.get(plan["instance_type"], False)
				if is_unavailable != plan["machine_unavailable"]:
					_mark_server_plan_as_unavailable(plan["name"])

			frappe.db.commit()
		except Exception:
			frappe.log_error(
				f"Failed to sync machine availability status for Server Plan {plan['name']}",
			)
			frappe.db.rollback()
