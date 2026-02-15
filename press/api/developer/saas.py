import json

import frappe
import frappe.utils
from frappe.rate_limiter import rate_limit

from press.api.developer import raise_invalid_key_error
from press.utils import mask_email


class SaasApiHandler:
	def __init__(self, secret_key):
		self.secret_key = secret_key
		self.validate_secret_key()

	def validate_secret_key(self):
		"""Validate secret_key and set app subscription name and doc"""

		if not self.secret_key or not isinstance(self.secret_key, str):
			raise_invalid_key_error()

		app_subscription_name = frappe.db.exists("Saas App Subscription", {"secret_key": self.secret_key})

		if not app_subscription_name:
			raise_invalid_key_error()

		self.app_subscription_name = app_subscription_name
		self.set_subscription_doc()

	def set_subscription_doc(self):
		"""To be called after `secret_key` validation"""
		self.app_subscription_doc = frappe.get_doc("Saas App Subscription", self.app_subscription_name)

	def get_subscription_status(self):
		return self.app_subscription_doc.status

	def get_subscription_info(self):
		return frappe.get_doc("Saas App Subscription", self.app_subscription_name)

	def get_plan_config(self):
		plan_doc = frappe.get_doc("Saas App Plan", self.app_subscription_doc.saas_app_plan).config

		return json.loads(plan_doc)

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

		domain = frappe.db.get_value("Saas App", self.app_subscription_doc.app, "custom_domain")
		return f"https://{domain}/api/method/press.api.saas.login_via_token?token={token}&team={self.app_subscription_doc.team}"

	def get_trial_expiry(self):
		return frappe.db.get_value("Site", self.app_subscription_doc.site, "trial_end_date")


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


@frappe.whitelist(allow_guest=True)
def get_subscription_info(secret_key):
	api_handler = SaasApiHandler(secret_key)
	return api_handler.get_subscription_info()


@frappe.whitelist(allow_guest=True)
def get_trial_expiry(secret_key):
	api_handler = SaasApiHandler(secret_key)
	return api_handler.get_trial_expiry()


"""
NOTE: These mentioned apis are used for all type of saas sites to allow login to frappe cloud
- send_verification_code
- verify_verification_code
- login_to_fc

Don't change the file name or the method names
It can potentially break the integrations.
"""


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def send_verification_code(domain: str, route: str = ""):
	from press.utils.otp import generate_otp

	domain_info = frappe.get_value("Site Domain", domain, ["site", "status"], as_dict=True)
	if not domain_info or domain_info.get("status") != "Active":
		frappe.throw(
			"The domain is not active currently. Please try again after activation. "
			'<a href="https://docs.frappe.io/cloud/sites/custom-domains" target="_blank">Learn more</a>'
		)

	site_info = frappe.get_value(
		"Site", domain_info.get("site"), ["name", "team", "standby_for", "standby_for_product"], as_dict=True
	)
	team_name = site_info.get("team")
	team_info = frappe.get_value("Team", team_name, ["name", "enabled", "user", "enforce_2fa"], as_dict=True)
	if not team_info or not team_info.get("enabled"):
		frappe.throw(
			"Your Frappe Cloud team is disabled currently. Please contact support to enable your team. "
		)

	check_if_user_can_login(team_info, site_info)

	# if is_user_logged_in(team_info.get("user")):
	# 	if route == "dashboard":
	# 		redirect_to = "/dashboard/"
	# 	elif route == "site-dashboard":
	# 		redirect_to = f"/dashboard/sites/{site_info.get('name')}"
	# 	return {"is_user_logged_in": True, "redirect_to": redirect_to}

	# generate otp and set in redis with 10 min expiry
	otp = generate_otp()
	frappe.cache.set_value(
		f"otp_hash_for_fc_login_via_saas_flow:{domain}",
		frappe.utils.sha256_hash(str(otp)),
		expires_in_sec=60 * 10,
	)

	email = team_info.get("user")
	send_email_with_verification_code(email, otp)

	return {
		"email": mask_email(email, 50),
		"is_user_logged_in": False,
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def verify_verification_code(domain: str, verification_code: str, route: str = "dashboard"):
	otp_hash = frappe.cache.get_value(f"otp_hash_for_fc_login_via_saas_flow:{domain}", expires=True)
	if not otp_hash or otp_hash != frappe.utils.sha256_hash(str(verification_code)):
		frappe.throw("Invalid Code. Please try again.")

	site = frappe.get_value("Site Domain", domain, "site")
	team = frappe.get_value("Site", site, "team")
	user = frappe.get_value("Team", team, "user")

	# as otp is valid, delete the otp from redis
	frappe.cache.delete_value(f"otp_hash_for_fc_login_via_saas_flow:{domain}")

	# login and generate a login_token to store sid
	login_token = frappe.generate_hash(length=64)
	frappe.cache.set_value(f"saas_fc_login_token:{login_token}", user, expires_in_sec=60)
	if route == "site-dashboard":
		frappe.cache.set_value(f"saas_fc_login_site:{login_token}", domain, expires_in_sec=60)

	frappe.response["login_token"] = login_token


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=5, seconds=60)
def login_to_fc(token: str):
	email_cache_key = f"saas_fc_login_token:{token}"
	domain_cache_key = f"saas_fc_login_site:{token}"
	email = frappe.cache.get_value(email_cache_key, expires=True)
	domain = frappe.cache.get_value(domain_cache_key, expires=True)

	if email:
		frappe.cache.delete_value(email_cache_key)
		frappe.local.login_manager.login_as(email)
	frappe.response.type = "redirect"
	if domain:
		frappe.cache.delete_value(domain_cache_key)
		frappe.response.location = f"/dashboard/sites/{domain}"
	else:
		frappe.response.location = "/dashboard/"


def is_user_logged_in(user):
	Sessions = frappe.qb.DocType("Sessions")

	return bool(
		frappe.qb.from_(Sessions)
		.select(Sessions.user)
		.where(Sessions.user == user)
		.where(Sessions.status == "Active")
		.run(as_dict=True)
	)


def check_if_user_can_login(team_info, site_info):
	if team_info.get("enforce_2fa"):
		frappe.throw(
			"Sorry, you cannot login with this method as 2FA is enabled. Please visit https://frappecloud.com/dashboard to login. "
			'<a href="https://docs.frappe.io/cloud/two-factor-authentication-2fa" target="_blank">Learn more</a>'
		)
	if (
		team_info.get("user") == "Administrator"
		or frappe.db.get_value("User", team_info.get("user"), "user_type") != "Website User"
	):
		frappe.throw(
			"Sorry, you cannot login with this method. Please contact support for more details. "
		)

	# restrict to SaaS Site
	if not (site_info.get("standby_for") or site_info.get("standby_for_product")):
		frappe.throw(
			"Only SaaS sites are allowed to login to Frappe Cloud via current method. "
			'<a href="https://docs.frappe.io/cloud/simplified-login-to-frappe-cloud-dashboard" target="_blank">Learn more</a>'
		)


def send_email_with_verification_code(email, otp):
	if frappe.conf.developer_mode:
		print("\nVerification Code for login to Frappe Cloud:")
		print(f"\nOTP for {email}:")
		print(otp)
		print()
	else:
		frappe.sendmail(
			recipients=email,
			subject="Verification Code for Frappe Cloud Login",
			template="verification_code_for_login",
			args={
				"full_name": frappe.get_value("User", email, "full_name"),
				"otp": otp,
				"image_path": "https://github.com/frappe/gameplan/assets/9355208/447035d0-0686-41d2-910a-a3d21928ab94",
			},
			now=True,
		)
