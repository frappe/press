import frappe

from typing import Dict


class InvalidSecretKeyError(Exception):
	http_status_code = 401


class DeveloperApiHandler:
	def __init__(self, secret_key: str) -> None:
		self.secret_key = secret_key
		self.validate_secret_key()

	def validate_secret_key(self):
		"""Validate secret_key and set app subscription name and doc"""
		app_subscription_name = frappe.db.exists(
			"Marketplace App Subscription", {"secret_key": self.secret_key},
		)

		if not app_subscription_name:
			frappe.throw("Please provide a valid secret key.", InvalidSecretKeyError)

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
			"marketplace_app_plan",
			"site",
			"interval",
			"end_date",
		]

		filtered_dict = {
			x: app_subscription_dict[x] for x in app_subscription_dict if x in fields_to_send
		}

		return filtered_dict


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
