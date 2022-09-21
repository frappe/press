# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import json
import requests
import frappe
from press.utils import log_error
from frappe.model.document import Document


class MarketplaceUsageRecord(Document):
	def validate(self):
		if not self.date:
			self.date = frappe.utils.today()

		if not self.time:
			self.time = frappe.utils.nowtime()

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
			),
			"plan": (
				"not in",
				frappe.get_all(
					"Plan", {"document_type": "Marketplace App", "price_usd": 0}, pluck="name"
				),
			),
			"status": "Active",
		},
		["name", "app", "site", "plan", "marketplace_app_plan", "team"],
	):
		team = frappe.db.get_value("Site", subscription["site"], "team")
		currency = frappe.db.get_value("Team", team, "currency")
		plan, price = frappe.db.get_value(
			"Plan", subscription["plan"], ["plan_title", f"price_{currency.lower()}"]
		)

		try:
			resp = requests.post(
				f"https://{subscription['site']}/api/method/{poll_methods[subscription['app']]}",
				data={"plan": plan},
			)
			if resp.status_code != 200:
				raise Exception

			result = json.loads(resp.text)["message"]
			amount = price / 31
			marketplace_add_ons = {
				rec["type"]: {
					"price_usd": rec["price_usd"] / 31,
					"price_inr": rec["price_inr"] / 31,
				}
				for rec in frappe.get_list(
					"Marketplace Add On",
					{"parent": subscription["marketplace_app_plan"]},
					["type", "price_usd", "price_inr"],
				)
			}

			for rec in result.items():
				price = marketplace_add_ons[rec[0]][f"price_{currency.lower()}"]
				amount += price * rec[1]  # quantity

			frappe.get_doc(
				{
					"doctype": "Marketplace Usage Record",
					"app": subscription["app"],
					"team": subscription["team"],
					"plan": subscription["marketplace_app_plan"],
					"currency": currency,
					"amount": amount,
					"marketplace_app_subscription": subscription["name"],
					"items": json.dumps(result),
				}
			).insert(ignore_permissions=True)
		except Exception as e:
			log_error(
				f"Marketplace Usage Record: Failed to poll site {subscription['site']}", data=e
			)
