# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from typing import List
from press.press.doctype.site_plan.plan import Plan


class MarketplaceAppPlan(Plan):
	dashboard_fields = ["app", "name", "title", "price_inr", "price_usd", "enabled"]

	@staticmethod
	def get_list_query(query):
		plans = query.run(as_dict=True)
		for plan in plans:
			plan["features"] = get_app_plan_features(plan.name)

		return plans

	@staticmethod
	def create_marketplace_app_subscription(
		site_name, app_name, plan_name, while_site_creation=False
	):
		marketplace_app = frappe.db.get_value("Marketplace App", {"app": app_name})
		subscription = frappe.db.exists(
			"Subscription",
			{
				"site": site_name,
				"document_type": "Marketplace App",
				"document_name": marketplace_app,
			},
		)

		# If already exists, update the plan and activate
		if subscription:
			subscription = frappe.get_doc(
				"Subscription",
				subscription,
				for_update=True,
			)

			subscription.plan = plan_name
			subscription.enabled = 1
			subscription.save(ignore_permissions=True)
			subscription.reload()

			return subscription

		return frappe.get_doc(
			{
				"doctype": "Subscription",
				"document_type": "Marketplace App",
				"document_name": app_name,
				"plan_type": "Marketplace App Plan",
				"plan": plan_name,
				"site": site_name,
				"team": frappe.local.team().name,
			}
		).insert(ignore_permissions=True)


def get_app_plan_features(app_plan: str) -> List[str]:
	features = frappe.get_all(
		"Plan Feature", filters={"parent": app_plan}, pluck="description", order_by="idx"
	)

	return features
