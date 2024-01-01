# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from press.utils import log_error
from frappe import _


@frappe.whitelist(allow_guest=True)
def login(product=None):
	flow = google_oauth_flow()
	authorization_url, state = flow.authorization_url()
	minutes = 5
	payload = {"state": state}
	if product:
		payload["product"] = product
	frappe.cache().set_value(
		f"google_oauth_flow:{state}", payload, expires_in_sec=minutes * 60
	)
	return authorization_url


@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):
	cached_key = f"google_oauth_flow:{state}"
	payload = frappe.cache().get_value(cached_key)
	if not payload:
		return invalid_login()

	product = payload.get("product")
	saas_product = (
		frappe.db.get_value("SaaS Product", product, ["name"], as_dict=1) if product else None
	)

	try:
		flow = google_oauth_flow()
		flow.fetch_token(authorization_response=frappe.request.url)
	except Exception as e:
		log_error("Google Login failed", data=e)
		frappe.local.response.type = "redirect"
		frappe.local.response.location = "/dashboard2/login"

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
		credentials = Credentials.from_authorized_user_info(
			json.loads(flow.credentials.to_json())
		)
		service = build("people", "v1", credentials=credentials)
		person = (
			service.people().get(resourceName="people/me", personFields="phoneNumbers").execute()
		)
		if person:
			phone = person.get("phoneNumbers")
			if phone:
				phone_number = phone[0].get("value")

	# saas product signup
	if saas_product:
		account_request = frappe.get_doc(
			doctype="Account Request",
			email=email,
			first_name=id_info.get("given_name"),
			last_name=id_info.get("family_name"),
			phone_number=phone_number,
			saas_product=saas_product.name,
		).insert(ignore_permissions=True)
		frappe.db.commit()

		frappe.local.response.type = "redirect"
		verification_url = account_request.get_verification_url()
		verification_url = verification_url.replace("dashboard", "dashboard2")
		frappe.local.response.location = verification_url
	else:
		# Frappe Cloud User Login
		team_exists, team_enabled = frappe.db.get_value(
			"Team", {"user": email}, ["name", "enabled"]
		) or [0, 0]
		if team_exists and team_enabled:
			# login to existing account
			frappe.local.login_manager.login_as(email)
			frappe.local.response.type = "redirect"
			frappe.local.response.location = "/dashboard2"
		elif team_exists and not team_enabled:
			# cannot login because account is disabled
			frappe.throw(_("Account {0} has been deactivated").format(email))
		elif not team_exists:
			account_request = frappe.get_doc(
				doctype="Account Request",
				email=email,
				first_name=id_info.get("given_name"),
				last_name=id_info.get("family_name"),
				phone_number=phone_number,
			).insert(ignore_permissions=True)
			frappe.db.commit()
			frappe.local.response.type = "redirect"
			verification_url = account_request.get_verification_url()
			verification_url = verification_url.replace("dashboard", "dashboard2")
			frappe.local.response.location = verification_url


def invalid_login():
	frappe.local.response["http_status_code"] = 401
	return "Invalid state parameter. The session timed out. Please try again or contact  Frappe Cloud support at https://frappecloud.com/support"


def google_oauth_flow():
	google_credentials = get_google_credentials()
	redirect_uri = google_credentials["web"].get("redirect_uris")[0]
	redirect_uri = redirect_uri.replace(
		"press.api.oauth.callback", "press.api.google.callback"
	)
	print(redirect_uri)
	flow = Flow.from_client_config(
		client_config=google_credentials,
		scopes=[
			"https://www.googleapis.com/auth/userinfo.profile",
			"openid",
			"https://www.googleapis.com/auth/userinfo.email",
		],
		redirect_uri=redirect_uri,
	)
	return flow


def get_google_credentials():
	if frappe.local.dev_server:
		import os

		# flow.fetch_token doesn't work with http, so this is needed for local development
		os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

	config = frappe.conf.get("google_credentials")
	if not config:
		frappe.throw("google_credentials not found in site_config.json")
	return config
