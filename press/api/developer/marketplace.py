import json
import frappe
from frappe.utils import get_url
from typing import Dict

from press.api.developer import raise_invalid_key_error
from press.api.marketplace import prepaid_saas_payment


class DeveloperApiHandler:
	def __init__(self, secret_key: str) -> None:
		self.secret_key = secret_key
		self.validate_secret_key()

	def validate_secret_key(self):
		"""Validate secret_key and set app subscription name and doc"""

		if not self.secret_key or not isinstance(self.secret_key, str):
			raise_invalid_key_error()

		app_subscription_name = frappe.db.exists(
			"Marketplace App Subscription", {"secret_key": self.secret_key, "status": "Active"}
		)

		if not app_subscription_name:
			raise_invalid_key_error()

		self.app_subscription_name = app_subscription_name
		self.set_subscription_doc()

	def set_subscription_doc(self):
		"""To be called after `secret_key` validation"""
		self.app_subscription_doc = frappe.get_doc(
			"Marketplace App Subscription", self.app_subscription_name
		)

	def get_subscription_status(self) -> str:
		return self.app_subscription_doc.status

	def get_subscription_info(self) -> Dict:
		"""Important rule for security: Send info back carefully"""
		app_subscription_dict = self.app_subscription_doc.as_dict()
		fields_to_send = [
			"app",
			"status",
			"plan",
			"site",
		]

		filtered_dict = {
			x: app_subscription_dict[x] for x in app_subscription_dict if x in fields_to_send
		}

		return filtered_dict

	def get_login_url(self):
		# check for active tokens
		team = frappe.db.get_value("Site", self.app_subscription_doc.site, "team")
		if frappe.db.exists(
			"Saas Remote Login",
			{
				"team": team,
				"status": "Attempted",
				"expires_on": (">", frappe.utils.now()),
			},
		):
			doc = frappe.get_doc(
				"Saas Remote Login",
				{
					"team": team,
					"status": "Attempted",
					"expires_on": (">", frappe.utils.now()),
				},
			)
			token = doc.token
		else:
			token = frappe.generate_hash("Saas Remote Login", 50)
			frappe.get_doc(
				{
					"doctype": "Saas Remote Login",
					"team": team,
					"token": token,
				}
			).insert(ignore_permissions=True)
			frappe.db.commit()

		return get_url(
			f"/api/method/press.api.marketplace.login_via_token?token={token}&team={team}&site={self.app_subscription_doc.site}"
		)

	def get_subscriptions(self):
		from press.api.marketplace import get_plans_for_app

		team = self.app_subscription_doc.team
		currency, address = frappe.db.get_value("Team", team, ["currency", "billing_address"])
		response = {"currency": currency, "address": True if address else False}
		response["subscriptions"] = [
			s.update(
				{
					"available_plans": get_plans_for_app(s["app"]),
					**frappe.db.get_value(
						"Marketplace App", s["app"], ["title", "image"], as_dict=True
					),
				}
			)
			for s in frappe.get_all(
				"Marketplace App Subscription",
				filters={"team": self.app_subscription_doc.team, "status": "Active"},
				fields=["name", "app", "site", "plan"],
			)
		]

		return response

	def update_billing_info(self, data: Dict) -> str:
		self.login_as_team()
		team_doc = frappe.get_doc("Team", self.app_subscription_doc.team)
		team_doc.update_billing_details(data)

		return "success"

	def saas_payment(self, data):
		self.login_as_team()
		return prepaid_saas_payment(
			self.app_subscription_name,
			self.app_subscription_doc.app,
			self.app_subscription_doc.site,
			data["new_plan"]["name"],
			data["total"],
			data["total"],
			data["billing"],
			False,
		)

	def login_as_team(self):
		frappe.local.login_manager.login_as(self.app_subscription_doc.team)


# ------------------------------------------------------------
# API ENDPOINTS
# ------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def get_subscription_status(secret_key: str) -> str:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_subscription_status()


@frappe.whitelist(allow_guest=True)
def get_subscription_info(secret_key: str) -> Dict:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_subscription_info()


@frappe.whitelist(allow_guest=True)
def get_login_url(secret_key: str) -> str:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_login_url()


@frappe.whitelist(allow_guest=True)
def get_subscriptions(secret_key: str) -> str:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_subscriptions()


@frappe.whitelist(allow_guest=True)
def update_billing_info(secret_key: str, data: Dict) -> str:
	data = frappe.parse_json(data)
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.update_billing_info(data)


@frappe.whitelist(allow_guest=True)
def saas_payment(secret_key: str, data: Dict) -> str:
	data = frappe.parse_json(data)
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.saas_payment(data)
