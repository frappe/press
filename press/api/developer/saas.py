import json
import frappe


class InvalidSecretKeyError(Exception):
	http_status_code = 401


class SaasApiHandler:
	def __init__(self, secret_key):
		self.secret_key = secret_key
		self.validate_secret_key()

	def validate_secret_key(self):
		"""Validate secret_key and set app subscription name and doc"""
		app_subscription_name = frappe.db.exists(
			"Saas App Subscription", {"secret_key": self.secret_key}
		)

		if not app_subscription_name:
			frappe.throw("Please provide a valid secret key.", InvalidSecretKeyError)

		self.app_subscription_name = app_subscription_name
		self.set_subscription_doc()

	def set_subscription_doc(self):
		"""To be called after `secret_key` validation"""
		self.app_subscription_doc = frappe.get_doc(
			"Saas App Subscription", self.app_subscription_name
		)

	def get_subscription_status(self):
		return self.app_subscription_doc.status

	def get_plan_config(self):
		plan_doc = frappe.get_doc(
			"Saas App Plan", self.app_subscription_doc.saas_app_plan
		).config

		return json.loads(plan_doc)


# ------------------------------------------------------------
# API ENDPOINTS
# ------------------------------------------------------------
@frappe.whitelist(allow_guest=True)
def ping():
	return "pong"


@frappe.whitelist(allow_guest=True)
def get_subscription_status(secret_key):
	api_handler = SaasApiHandler(secret_key)
	return api_handler.get_subscription_status()


@frappe.whitelist(allow_guest=True)
def get_plan_config(secret_key):
	api_handler = SaasApiHandler(secret_key)
	return api_handler.get_plan_config()
