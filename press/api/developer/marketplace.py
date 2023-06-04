import frappe
from frappe.utils import get_url
from typing import Dict, List

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
			"end_date",
		]

		filtered_dict = {
			x: app_subscription_dict[x] for x in app_subscription_dict if x in fields_to_send
		}

		return filtered_dict

	def get_subscriptions(self) -> Dict:
		team = self.app_subscription_doc.team
		with SessionManager(team) as _:
			from press.api.marketplace import get_plans_for_app
			from press.utils.telemetry import capture

			currency, address = frappe.db.get_value(
				"Team", team, ["currency", "billing_address"]
			)
			response = {
				"currency": currency,
				"address": True if address else False,
				"team": self.app_subscription_doc.team,
				"countries": frappe.db.get_all("Country", pluck="name"),
			}
			response["subscriptions"] = [
				s.update(
					{
						"available_plans": get_plans_for_app(app_name=s["app"], include_free=False),
						**frappe.db.get_value(
							"Marketplace App", s["app"], ["title", "image"], as_dict=True
						),
					}
				)
				for s in frappe.get_all(
					"Marketplace App Subscription",
					filters={
						"team": self.app_subscription_doc.team,
						"status": "Active",
						"site": self.app_subscription_doc.site,
						"app": (
							"in",
							frappe.get_all("Saas Settings", {"billing_type": "prepaid"}, pluck="name"),
						),
					},
					fields=["name", "app", "site", "plan"],
				)
			]

			capture("clicked_subscribe_button", "fc_signup", team)

			return response

	def get_plans(self, subscription):
		team = self.app_subscription_doc.team
		with SessionManager(team) as _:
			from press.api.marketplace import get_plans_for_app

			return get_plans_for_app(
				frappe.db.get_value("Marketplace App Subscription", subscription, "app"),
				include_free=False,
			)

	def update_billing_info(self, data: Dict) -> str:
		team = self.app_subscription_doc.team
		with SessionManager(team) as _:
			team_doc = frappe.get_doc("Team", team)
			team_doc.update_billing_details(data)

			return "success"

	def saas_payment(self, data: Dict) -> Dict:
		with SessionManager(self.app_subscription_doc.team) as _:
			return prepaid_saas_payment(
				data["sub_name"],
				data["app"],
				data["site"],
				data["new_plan"]["name"],
				data["total"],
				data["total"],
				12 if data["billing"] == "annual" else 1,
				False,
			)

	def send_login_link(self):
		try:
			login_url = self.get_login_url()
			users = frappe.get_doc("Team", self.app_subscription_doc.team).user
			frappe.sendmail(
				subject="Login Verification Email",
				recipients=[users],
				template="remote_login",
				args={"login_url": login_url, "site": self.app_subscription_doc.site},
				now=True,
			)
			return "success"
		except Exception as e:
			return e

	def get_login_url(self):
		# check for active tokens
		team = self.app_subscription_doc.team
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


class SessionManager:
	# set user for authenticated requests and then switch to guest once completed
	def __init__(self, team: str):
		frappe.set_user(frappe.db.get_value("Team", team, "user"))

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, exc_traceback):
		frappe.set_user("Guest")


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
def get_subscriptions(secret_key: str) -> str:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_subscriptions()


@frappe.whitelist(allow_guest=True)
def get_plans(secret_key: str, subscription: str) -> List:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_plans(subscription)


@frappe.whitelist(allow_guest=True)
def update_billing_info(secret_key: str, data) -> str:
	data = frappe.parse_json(data)
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.update_billing_info(data)


@frappe.whitelist(allow_guest=True)
def saas_payment(secret_key: str, data) -> str:
	data = frappe.parse_json(data)
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.saas_payment(data)


@frappe.whitelist(allow_guest=True)
def send_login_link(secret_key: str) -> str:
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.send_login_link()
