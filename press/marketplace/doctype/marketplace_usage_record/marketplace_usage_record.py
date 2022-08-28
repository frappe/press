# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from press.utils import log_error
from frappe.model.document import Document


class MarketplaceUsageRecord(Document):
	def after_insert(self):
		team = frappe.get_doc("Team", self.team)

		available_credits = team.get_balance()
		if available_credits < self.amount:
			frappe.get_doc("Site", self.site).suspend()
			available = frappe.utils.fmt_money(available_credits, 2, self.currency)
			frappe.throw(
				f"Available credits ({available}) is less than daily consumption amount"
				f" ({self.get_formatted('amount')})"
			)

		remark = "Consuming credits for Marketplace Usage Record."
		amount = self.amount * -1
		team.allocate_credit_amount(
			amount,
			source="",
			remark=f"{remark}, Ref: Marketplace App Subscription {self.marketplace_app_subscription}",
		)


def create_marketplace_usage_record():
	poll_methods = {
		app["name"]: app["poll_method"]
		for app in frappe.get_all("Marketplace App", ["name", "poll_method"])
	}

	for subscription in frappe.get_all(
		"Marketplace App Subscription",
		{
			"app": (
				"in",
				frappe.get_all("Saas Settings", {"billing_type": "prepaid"}, pluck="name"),
			)
		},
		["name", "app", "site", "plan", "marketplace_app_plan", "team"],
	):

		currency = frappe.db.get_value("Team", subscription["team"], "currency")
		plan, price = frappe.db.get_value(
			"Plan", subscription["plan"], ["plan_title", f"price_{currency.lower()}"]
		)
		data = {
			"plan": plan,
			"currency": currency,
			"app": subscription["app"],
			"price": price,
		}

		try:
			resp = requests.post(
				f"https://{subscription['site']}/api/method/{poll_methods[subscription['app']]}",
				data=data,
			)
			result = json.loads(resp.text)["message"]
			frappe.get_doc(
				{
					"doctype": "Marketplace Usage Record",
					"app": result["app"],
					"team": subscription["team"],
					"plan": subscription["marketplace_app_plan"],
					"currency": result["currency"],
					"amount": result["amount"],
					"marketplace_app_subscription": subscription["name"],
					"items": json.dumps(result["addons"]),
				}
			).insert(ignore_permissions=True)
		except Exception as e:
			log_error(
				f"Marketplace Usage Record: Failed to poll site {subscription['site']}", data=e
			)
