# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

from typing import TYPE_CHECKING

import frappe

from press.press.doctype.site_plan.plan import Plan
from press.utils.jobs import has_job_timeout_exceeded

if TYPE_CHECKING:
	from press.press.doctype.cluster.cluster import Cluster


class ServerPlan(Plan):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		allow_unified_server: DF.Check
		cluster: DF.Link | None
		disk: DF.Int
		enabled: DF.Check
		ignore_machine_availability_sync: DF.Check
		instance_type: DF.Data | None
		legacy_plan: DF.Check
		machine_unavailable: DF.Check
		memory: DF.Int
		plan_type: DF.Link | None
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
		"plan_type",
		"allow_unified_server",
		"machine_unavailable",
	)

	def get_doc(self, doc):
		doc["price_per_day_inr"] = self.get_price_per_day("INR")
		doc["price_per_day_usd"] = self.get_price_per_day("USD")
		return doc

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


def sync_machine_availability_status_of_plans():
	frappe.enqueue(
		_sync_machine_availability_status_of_plans,
		timeout=3600,
		deduplicate=True,
		job_id="sync_machine_availability_status_of_plans",
	)


def _sync_machine_availability_status_of_plans():  # noqa
	plans = frappe.get_all(
		"Server Plan",
		filters={"ignore_machine_availability_sync": 0, "enabled": 1},
		fields=["name", "cluster", "machine_unavailable", "instance_type"],
	)
	cluster_doc_map: dict[str, Cluster] = {}
	cluster_plans: dict[str, list[dict]] = {}

	for plan in plans:
		if has_job_timeout_exceeded():
			return

		if not plan.instance_type:
			continue

		if plan.cluster not in cluster_doc_map:
			cluster_doc_map[plan.cluster] = frappe.get_doc("Cluster", plan.cluster)

		if plan.cluster not in cluster_plans:
			cluster_plans[plan.cluster] = []
		cluster_plans[plan.cluster].append(plan)

	for c in cluster_plans:
		if has_job_timeout_exceeded():
			return

		try:
			cluster: Cluster = frappe.get_doc("Cluster", c)
			plan_availability_results: dict[str, bool] = cluster.check_machine_availability(
				[p["instance_type"] for p in cluster_plans[c]]
			)

			for plan in cluster_plans[c]:
				is_unavailable = not plan_availability_results.get(plan.instance_type, False)
				if is_unavailable != plan.machine_unavailable:
					frappe.db.set_value("Server Plan", plan.name, "machine_unavailable", is_unavailable)

			frappe.db.commit()
		except Exception:
			frappe.log_error(
				f"Failed to sync machine availability status for Server Plan {plan.name}",
			)
			frappe.db.rollback()
