import os

import json
import frappe

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token


from press.api.account import get_account_request_from_key

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
			"https://www.googleapis.com/auth/user.addresses.read",
			"https://www.googleapis.com/auth/user.phonenumbers.read",
			"https://www.googleapis.com/auth/contacts.readonly",
		],
		redirect_uri=redirect_uri,
	)
	return flow


@frappe.whitelist(allow_guest=True)
def google_login(saas_app=None):
	flow = google_oauth_flow()
	authorization_url, state = flow.authorization_url()
	minutes = 10
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

	if not state == cached_state or saas_app:
		frappe.local.response["http_status_code"] = 401
		return {"message": "Invalid state parameter"}

	try:
		flow = google_oauth_flow()
		flow.fetch_token(authorization_response=frappe.request.url)
	except Exception as e:
		frappe.throw(e)

	# id_info
	token_request = Request()
	id_info = id_token.verify_oauth2_token(
		id_token=flow.credentials._id_token,
		request=token_request,
		audience=frappe.conf.get("google_oauth_config")["web"]["client_id"],
	)

	email = id_info.get("email")

	# phone and address (this may return nothing if info doesn't exists)
	credentials = Credentials.from_authorized_user_info(
		json.loads(flow.credentials.to_json())
	)
	service = build("people", "v1", credentials=credentials)
	person = (
		service.people()
		.get(resourceName="people/me", personFields="addresses,phoneNumbers")
		.execute()
	)
	print(person)

	if not frappe.db.exists("User", email):  # signup
		account_request = frappe.get_doc(
			{
				"doctype": "Account Request",
				"team": email,
				"email": email,
				"first_name": id_info.get("given_name"),
				"last_name": id_info.get("family_name"),
				"send_email": False,
				"role": "Press Admin",
				"oauth_signup": True,
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()

		frappe.local.response.type = "redirect"
		if saas_app:  # saas signup
			frappe.local.response.location = (
				f"/saas-oauth.html?app={saas_app}?key={account_request.request_key}"
			)
		else:  # dashbaord signup
			frappe.local.response.location = (
				f"/dashboard/setup-account/{account_request.request_key}"
			)
	else:  # login
		frappe.local.login_manager.login_as(email)
		frappe.local.response.type = "redirect"
		frappe.response.location = "/dashboard"


@frappe.whitelist(allow_guest=True)
def saas_setup(key, app, country):
	account_request = get_account_request_from_key(key)

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
		}
	).insert(ignore_permissions=True)

	site = get_site(app)

	if site.status == "Active":
		signup_ar.subdomain = site.subdomain
		sid = site.get_login_sid()
		return f"https://{site.name}/desk?sid={sid}"
	else:
		from frappe.utils import get_url

		return get_url("/prepare-site.html?key={signup_ar.key}&app={app}")


def get_site(app):
	# Returns a standby site (if ready) or Creates a new one
	# TODO: add marketplace subscription keys to standby sites as well
	site = None
	from press.press.doctype.site.saas_pool import get as get_pooled_saas_site

	pooled_site = get_pooled_saas_site(app)
	if pooled_site:
		site = pooled_site
	else:
		# create a new site by hybrid pools conditioning (site=new_site_doc)
		# redirect to prepaire-site.html
		pass
	return frappe.get_doc("Site", site)
