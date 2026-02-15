# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import annotations

import frappe
from frappe import _
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from oauthlib.oauth2 import AccessDeniedError

from press.utils import log_error
from press.utils.telemetry import capture


@frappe.whitelist(allow_guest=True)
def login(product=None):
	flow = google_oauth_flow()
	authorization_url, state = flow.authorization_url()
	minutes = 5
	payload = {"state": state}
	if product:
		payload["product"] = product
	frappe.cache().set_value(f"google_oauth_flow:{state}", payload, expires_in_sec=minutes * 60)
	return authorization_url


@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):  # noqa: C901
	cached_key = f"google_oauth_flow:{state}"
	payload = frappe.cache().get_value(cached_key)
	if not payload:
		return invalid_login()

	product = payload.get("product")
	product_trial = frappe.db.get_value("Product Trial", product, ["name"], as_dict=1) if product else None

	def _redirect_to_login_on_failed_authentication():
		frappe.local.response.type = "redirect"
		if product_trial:
			frappe.local.response.location = f"/dashboard/login?product={product_trial.name}"
		else:
			frappe.local.response.location = "/dashboard/login"

	try:
		flow = google_oauth_flow()
		flow.fetch_token(authorization_response=frappe.request.url)
	except AccessDeniedError:
		_redirect_to_login_on_failed_authentication()
		return None
	except Exception as e:
		log_error("Google Login failed", data=e)
		_redirect_to_login_on_failed_authentication()
		return None

	# authenticated
	frappe.cache().delete_value(cached_key)

	# id_info
	token_request = Request()
	google_credentials = get_google_credentials()
	id_info = id_token.verify_oauth2_token(
		id_token=flow.credentials._id_token,
		request=token_request,
		audience=google_credentials["web"]["client_id"],
	)

	email = id_info.get("email")

	team_name, team_enabled = frappe.db.get_value("Team", {"user": email}, ["name", "enabled"]) or [0, 0]

	if team_name and not team_enabled:
		frappe.throw(
			_("Account {0} has been deactivated. Please contact support to reactivate your account. ").format(email)
		)
		return None

	# if team exitst and  oauth is not using in saas login/signup flow
	if team_name and not product_trial:
		has_2fa = frappe.db.get_value("User 2FA", {"user": email, "enabled": 1})
		if has_2fa:
			# redirect to 2fa page
			frappe.respond_as_web_page(
				_("Two-Factor Authentication Required"),
				_(
					"Google OAuth login doesn't support 2FA. Please login using your email and verification code / password."
				),
				primary_action="/dashboard/login",
				primary_label=_("Login with Email"),
			)
			return None

		# login to existing account
		frappe.local.login_manager.login_as(email)
		frappe.local.response.type = "redirect"
		frappe.local.response.location = "/dashboard"
		return None

	# create account request
	account_request = frappe.get_doc(
		doctype="Account Request",
		email=email,
		first_name=id_info.get("given_name"),
		last_name=id_info.get("family_name"),
		role="Press Admin",
		oauth_signup=True,
		product_trial=product_trial.name if product_trial else None,
	)
	account_request.insert(ignore_permissions=True)
	frappe.db.commit()

	if product_trial:
		# dummy event so that the stat in funnel won't break
		capture("otp_verified", "fc_product_trial", account_request.name)

	if team_name and product_trial:
		frappe.local.login_manager.login_as(email)
		frappe.local.response.type = "redirect"
		frappe.local.response.location = f"/dashboard/create-site/{product_trial.name}/setup"
	else:
		# create/setup account
		frappe.local.response.type = "redirect"
		frappe.local.response.location = account_request.get_verification_url()
	return None


def invalid_login():
	frappe.local.response["http_status_code"] = 401
	return "Invalid state parameter. The session timed out. Please try again or contact  Frappe Cloud support at https://frappecloud.com/support"


def google_oauth_flow():
	google_credentials = get_google_credentials()
	redirect_uri = google_credentials["web"].get("redirect_uris")[0]
	redirect_uri = redirect_uri.replace("press.api.oauth.callback", "press.api.google.callback")
	return Flow.from_client_config(
		client_config=google_credentials,
		scopes=[
			"https://www.googleapis.com/auth/userinfo.profile",
			"openid",
			"https://www.googleapis.com/auth/userinfo.email",
		],
		redirect_uri=redirect_uri,
	)


def get_google_credentials():
	if frappe.local.dev_server:
		import os

		# flow.fetch_token doesn't work with http, so this is needed for local development
		os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

	config = frappe.conf.get("google_credentials")
	if not config:
		frappe.throw(
			"Google credentials not found in site_config.json. Please configure Google OAuth credentials for your site. "
			'<a href="https://docs.frappe.io/framework/user/en/integration/google_drive" target="_blank">Learn more</a>'
		)
	return config
