# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from typing import ClassVar

import frappe
from frappe import cint

from press.press.doctype.site_plan.plan import Plan


def get_permission_query_conditions(user: str | None = None) -> str:
	if not user:
		user = frappe.session.user

	if frappe.db.get_value("User", user, "user_type", cache=True) == "System User":
		return ""

	from press.utils import get_current_team

	MarketplaceApp = frappe.qb.DocType("Marketplace App")
	MarketplaceAppPlan = frappe.qb.DocType("Marketplace App Plan")
	permitted_apps = (
		frappe.qb.from_(MarketplaceApp)
		.select(MarketplaceApp.name)
		.where(MarketplaceApp.team == get_current_team())
	)
	return MarketplaceAppPlan.app.isin(permitted_apps).get_sql()


def has_permission(doc, ptype: str, user: str | None = None) -> bool:
	if not user:
		user = frappe.session.user

	if frappe.db.get_value("User", user, "user_type", cache=True) == "System User":
		return True

	if ptype == "create" and not doc.app:
		return False

	from press.access.support_access import has_support_access
	from press.utils import get_current_team

	if has_support_access("Marketplace App", doc.app):
		return True

	return frappe.db.get_value("Marketplace App", doc.app, "team") == get_current_team()


class MarketplaceAppPlan(Plan):
	dashboard_fields: ClassVar = ["app", "name", "title", "price_inr", "price_usd", "enabled"]

	@staticmethod
	def get_list_query(query):
		plans = query.run(as_dict=True)
		for plan in plans:
			plan["features"] = get_app_plan_features(plan.name)

		return plans

	def after_insert(self):
		self.update_marketplace_app_subscription_type()

	def on_update(self):
		self.update_marketplace_app_subscription_type()

	def update_marketplace_app_subscription_type(self):
		if cint(self.price_inr) > 0 or cint(self.price_usd) > 0:
			frappe.db.set_value(
				"Marketplace App",
				self.app,
				"subscription_type",
				"Paid",
			)

	@staticmethod
	def create_marketplace_app_subscription(
		site_name, app_name, plan_name, team_name, while_site_creation=False
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
				"team": team_name,
			}
		).insert(ignore_permissions=True)


def get_app_plan_features(app_plan: str) -> list[str]:
	return frappe.get_all("Plan Feature", filters={"parent": app_plan}, pluck="description", order_by="idx")
