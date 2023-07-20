import json
import frappe

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token

from frappe.utils import get_url
from frappe.core.utils import find

from press.api.account import get_account_request_from_key, setup_account
from press.api.saas import (
	check_subdomain_availability,
	create_marketplace_subscription,
	create_or_rename_saas_site,
)
from press.press.doctype.site.saas_site import get_saas_domain
from press.utils import log_error


import os

from press.utils.telemetry import capture, identify

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


def google_oauth_flow():
	config = frappe.conf.get("google_oauth_config")
	redirect_uri = config["web"].get("redirect_uris")[0]
	flow = Flow.from_client_config(
		client_config=config,
		scopes=[
			"https://www.googleapis.com/auth/userinfo.profile",
			"openid",
			"https://www.googleapis.com/auth/userinfo.email",
		],
		redirect_uri=redirect_uri,
	)
	return flow


@frappe.whitelist(allow_guest=True)
def google_login(saas_app=None):
	flow = google_oauth_flow()
	authorization_url, state = flow.authorization_url()
	minutes = 5
	frappe.cache().set_value(
		f"fc_oauth_state:{state}", saas_app or state, expires_in_sec=minutes * 60
	)
	return authorization_url


@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):
	cached_key = f"fc_oauth_state:{state}"
	cached_state = frappe.cache().get_value(cached_key)
	saas_app = cached_state in frappe.db.get_all("Saas Settings", pluck="name")
	frappe.cache().delete_value(cached_key)

	if (state == cached_state) or (saas_app):
		pass
	else:
		frappe.local.response["http_status_code"] = 401
		return "Invalid state parameter. The session timed out. Please try again or contact  Frappe Cloud support at https://frappecloud.com/support"

	try:
		flow = google_oauth_flow()
		flow.fetch_token(authorization_response=frappe.request.url)
	except Exception as e:
		log_error("Google oauth Login failed", data=e)
		frappe.local.response.type = "redirect"
		frappe.local.response.location = "/dashboard/login"

	# id_info
	token_request = Request()
	id_info = id_token.verify_oauth2_token(
		id_token=flow.credentials._id_token,
		request=token_request,
		audience=frappe.conf.get("google_oauth_config")["web"]["client_id"],
	)

	email = id_info.get("email")

	# phone (this may return nothing if info doesn't exists)
	number = ""
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
				number = phone[0].get("value")

	# saas signup
	if saas_app and cached_state:
		account_request = create_account_request(
			email=email,
			first_name=id_info.get("given_name"),
			last_name=id_info.get("family_name"),
			phone_number=number,
		)

		logo = frappe.db.get_value("Saas Signup Generator", cached_state, "image_path")
		frappe.local.response.type = "redirect"
		frappe.local.response.location = get_url(
			f"/saas-oauth.html?app={cached_state}&key={account_request.request_key}&domain={get_saas_domain(cached_state)}&logo={logo}"
		)
	else:
		# fc login or signup
		if not frappe.db.exists("User", email):
			account_request = create_account_request(
				email=email,
				first_name=id_info.get("given_name"),
				last_name=id_info.get("family_name"),
				phone_number=number,
			)
			frappe.local.response.type = "redirect"
			frappe.local.response.location = (
				f"/dashboard/setup-account/{account_request.request_key}"
			)
		# login
		else:
			frappe.local.login_manager.login_as(email)
			frappe.local.response.type = "redirect"
			frappe.response.location = "/dashboard"


def create_account_request(email, first_name, last_name, phone_number=""):
	account_request = frappe.get_doc(
		{
			"doctype": "Account Request",
			"team": email,
			"email": email,
			"first_name": first_name,
			"last_name": last_name,
			"phone_number": phone_number,
			"send_email": False,
			"role": "Press Admin",
			"oauth_signup": True,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	return account_request


@frappe.whitelist(allow_guest=True)
def saas_setup(key, app, country, subdomain):
	if not check_subdomain_availability(subdomain, app):
		frappe.throw(f"Subdomain {subdomain} is already taken")

	all_countries = frappe.db.get_all("Country", pluck="name")
	country = find(all_countries, lambda x: x.lower() == country.lower())
	if not country:
		frappe.throw("Country filed should be a valid country name")

	# create team and user
	account_request = get_account_request_from_key(key)
	if not frappe.db.exists("Team", {"user": account_request.email}):
		setup_account(
			key=key,
			first_name=account_request.first_name,
			last_name=account_request.last_name,
			country=country,
			accepted_user_terms=True,
			oauth_signup=True,
		)

	# create a signup account request
	signup_ar = frappe.get_doc(
		{
			"doctype": "Account Request",
			"team": account_request.team,
			"email": account_request.email,
			"first_name": account_request.first_name,
			"last_name": account_request.last_name,
			"emaill": account_request.email,
			"saas": True,
			"erpnext": False,
			"saas_app": app,
			"role": "Press Admin",
			"country": country,
			"subdomain": subdomain,
		}
	).insert(ignore_permissions=True)
	site_name = signup_ar.get_site_name()
	identify(
		site_name,
		app=app,
		oauth=True,
	)
	capture("completed_oauth_account_request", "fc_saas", site_name)
	create_or_rename_saas_site(app, signup_ar)
	frappe.set_user("Administrator")
	create_marketplace_subscription(signup_ar)

	return get_url("/prepare-site?key=" + signup_ar.request_key + "&app=" + app)
