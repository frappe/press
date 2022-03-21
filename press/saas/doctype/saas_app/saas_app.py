# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.saas.doctype.saas_app_plan.saas_app_plan import get_app_plan_features


class SaasApp(Document):
	def autoname(self):
		self.name = self.app

	def get_app_versions(self):
		v = [ver.version_name for ver in self.app_versions]
		return v

	def get_plans(self):
		return get_plans_for_app(self.name)


def get_plans_for_app(app):
	plans = []
	saas_app_plans = frappe.get_all(
		"Saas App Plan",
		filters={"app": app, "enabled": 1},
		fields=["name", "plan", "is_free"],
	)

	for app_plan in saas_app_plans:
		plan_data = {}
		plan_data.update(app_plan)

		plan_prices = get_plan_prices(app_plan.plan)
		plan_data.update(plan_prices)

		plan_data["features"] = get_app_plan_features(app_plan.name)

		plans.append(plan_data)

	plans.sort(key=lambda x: x["price_usd"])

	return plans


def get_plan_prices(plan_name):
	plan_prices = frappe.db.get_value(
		"Plan", plan_name, ["plan_title", "price_usd", "price_inr"], as_dict=True
	)

	return plan_prices
