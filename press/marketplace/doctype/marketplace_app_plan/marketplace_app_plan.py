# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

import frappe

from typing import List
from frappe.model.document import Document


class MarketplaceAppPlan(Document):
	@staticmethod
	def create_marketplace_app_subscription(
		site_name, app_name, plan_name, while_site_creation=False
	):
		marketplace_app_name = frappe.db.get_value("Marketplace App", {"app": app_name})
		app_subscription = frappe.db.exists(
			"Marketplace App Subscription", {"site": site_name, "app": marketplace_app_name}
		)

		# If already exists, update the plan and activate
		if app_subscription:
			app_subscription = frappe.get_doc(
				"Marketplace App Subscription",
				app_subscription,
				for_update=True,
			)

			app_subscription.marketplace_app_plan = plan_name
			app_subscription.status = "Active"
			app_subscription.save(ignore_permissions=True)
			app_subscription.reload()

			return app_subscription

		return frappe.get_doc(
			{
				"doctype": "Marketplace App Subscription",
				"marketplace_app_plan": plan_name,
				"app": app_name,
				"site": site_name,
				"team": frappe.local.team().name,
				"while_site_creation": while_site_creation,
			}
		).insert(ignore_permissions=True)

	def validate(self):
		self.validate_plan()
		self.mark_free_if_applicable()

	def validate_plan(self):
		dt = frappe.db.get_value("Plan", self.plan, "document_type")

		if dt != "Marketplace App":
			frappe.throw("The plan must be a Marketplace App plan.")

	def mark_free_if_applicable(self):
		if frappe.db.get_value("Plan", self.plan, "price_usd") == 0:
			self.is_free = True
		else:
			self.is_free = False


def get_app_plan_features(app_plan: str) -> List[str]:
	features = frappe.get_all(
		"Plan Feature", filters={"parent": app_plan}, pluck="description", order_by="idx"
	)

	return features
