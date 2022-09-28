import frappe
from frappe.utils import get_url
from typing import Dict

from press.api.developer import raise_invalid_key_error


class DeveloperApiHandler:
	def __init__(self, secret_key: str) -> None:
		self.secret_key = secret_key
		self.validate_secret_key()

	def validate_secret_key(self):
		"""Validate secret_key and set app subscription name and doc"""

		if not self.secret_key or not isinstance(self.secret_key, str):
			raise_invalid_key_error()

		app_subscription_name = frappe.db.exists(
			"Marketplace App Subscription", {"secret_key": self.secret_key}
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
def get_login_url(secret_key):
	api_handler = DeveloperApiHandler(secret_key)
	return api_handler.get_login_url()
