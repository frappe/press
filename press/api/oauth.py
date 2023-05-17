# from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2 import id_token

import frappe


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
def google_login():
	flow = google_oauth_flow()
	authorization_url, state = flow.authorization_url()
	minutes = 10
	frappe.cache().set_value(f"fc_oauth_state:{state}", state, expires_in_sec=minutes * 60)
	return authorization_url


@frappe.whitelist(allow_guest=True)
def callback(code=None, state=None):
	cached_key = f"fc_oauth_state:{state}"
	cached_state = frappe.cache().get_value(cached_key)
	frappe.cache().delete_value(cached_key)
	if not state == cached_state:
		frappe.local.response["http_status_code"] = 401
		return {"message": "Invalid state parameter"}

	try:
		flow = google_oauth_flow()
		flow.fetch_token(authorization_response=frappe.request.url, code=code)
	except Exception as e:
		frappe.throw(e)

	# credentials = Credentials.from_authorized_user_info(
	# json.loads(flow.credentials.to_json())
	# )
	token_request = Request()
	id_info = id_token.verify_oauth2_token(
		id_token=flow.credentials._id_token,
		request=token_request,
		audience=frappe.conf.get("google_oauth_config")["web"]["client_id"],
	)

	email = id_info.get("email")

	if not frappe.db.exists("User", email):
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
		frappe.local.response.type = "redirect"
		frappe.local.response.location = (
			f"/dashboard/setup-account?key={account_request.request_key}"
		)
	else:
		frappe.local.login_manager.login_as(email)
		frappe.local.response.type = "redirect"
		frappe.response.location = "/dashboard"
