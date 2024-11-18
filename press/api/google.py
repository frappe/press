# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import annotations

import json

import frappe
from frappe import _
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from oauthlib.oauth2 import AccessDeniedError

from press.api.product_trial import _get_active_site as get_active_site_product_trial
from press.api.product_trial import setup_account as setup_account_product_trial
from press.utils import log_error


@frappe.whitelist(allow_guest=True)
def login(product=None, country=None):
	flow = google_oauth_flow()
	authorization_url, state = flow.authorization_url()
	minutes = 5
	payload = {"state": state}
	if product:
		payload["product"] = product
	if country:
		payload["country"] = country
	frappe.cache().set_value(f"google_oauth_flow:{state}", payload, expires_in_sec=minutes * 60)
	return authorization_url


@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):  # noqa: C901
	cached_key = f"google_oauth_flow:{state}"
	payload = frappe.cache().get_value(cached_key)
	if not payload:
		return invalid_login()

	country = payload.get("country")
	product = payload.get("product")
	product_trial = frappe.db.get_value("Product Trial", product, ["name"], as_dict=1) if product else None

	def _redirect_to_login_on_failed_authentication():
		frappe.local.response.type = "redirect"
		if product_trial:
			frappe.local.response.location = f"/dashboard/saas/{product_trial.name}/login"
		else:
			frappe.local.response.location = "/dashboard/login"

	def _redirect_to_target_on_successful_authentication(team_name: str | None = None):
		frappe.local.response.type = "redirect"
		if product_trial:
			if get_active_site_product_trial(product_trial.name, team_name):
				frappe.local.response.location = f"/dashboard/saas/{product_trial.name}/login-to-site"
			else:
				frappe.local.response.location = f"/dashboard/saas/{product_trial.name}/setup"
		else:
			frappe.local.response.location = "/dashboard"

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

	# phone (this may return nothing if info doesn't exists)
	phone_number = ""
	if flow.credentials.refresh_token:  # returns only for the first authorization
		credentials = Credentials.from_authorized_user_info(json.loads(flow.credentials.to_json()))
		service = build("people", "v1", credentials=credentials)
		person = service.people().get(resourceName="people/me", personFields="phoneNumbers").execute()
		if person and person.get("phoneNumbers"):
			phone_number = person.get("phoneNumbers")[0].get("value")

	team_name, team_enabled = frappe.db.get_value("Team", {"user": email}, ["name", "enabled"]) or [0, 0]

	if team_name and not team_enabled:
		frappe.throw(_("Account {0} has been deactivated").format(email))
		return None

	if team_name:
		# login to existing account
		frappe.local.login_manager.login_as(email)
		_redirect_to_target_on_successful_authentication()
		return None

	# create account request
	account_request = frappe.get_doc(
		doctype="Account Request",
		email=email,
		first_name=id_info.get("given_name"),
		last_name=id_info.get("family_name"),
		phone_number=phone_number,
		role="Press Admin",
	)
	if product_trial:
		if not country:
			frappe.throw(_("Please provide a valid country name"))
		account_request.country = country
		account_request.product_trial = product_trial.name

	account_request.insert(ignore_permissions=True)

	if not account_request.product_trial:
		frappe.local.response.type = "redirect"
		frappe.local.response.location = account_request.get_verification_url()
		frappe.db.commit()
		return None

	# setup account product trial
	response = setup_account_product_trial(account_request.key)
	frappe.db.commit()

	frappe.local.response.type = "redirect"
	frappe.local.response.location = response.get("location")
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
		frappe.throw("google_credentials not found in site_config.json")
	return config
