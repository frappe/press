# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
import requests

from press.api.github import decode_github_oauth_state, get_github_callback_login_redirect
from press.utils import get_valid_teams_for_user, log_error


def get_context(context):
	code = frappe.form_dict.code
	state = frappe.form_dict.state
	redirect_url = frappe.utils.get_url("/dashboard")

	if frappe.session.user == "Guest":
		frappe.flags.redirect_location = get_github_callback_login_redirect(code, state)
		raise frappe.Redirect

	if code and state:
		try:
			decoded_state = decode_github_oauth_state(state)
			team = decoded_state["team"]
			valid_teams = {
				team_doc["name"] for team_doc in get_valid_teams_for_user(frappe.session.user)
			}
			if team not in valid_teams:
				raise frappe.PermissionError("Not permitted to update this team's GitHub access token")

			redirect_url = frappe.utils.get_url(decoded_state["redirect_url"])
			obtain_access_token(code, team)
			frappe.db.commit()
		except Exception:
			log_error("GitHub OAuth Authorization Error")

	frappe.flags.redirect_location = redirect_url
	raise frappe.Redirect


def obtain_access_token(code, team):
	response = None
	try:
		client_id = frappe.db.get_single_value("Press Settings", "github_app_client_id")
		client_secret = frappe.db.get_single_value(
			"Press Settings", "github_app_client_secret"
		)
		data = {"client_id": client_id, "client_secret": client_secret, "code": code}
		headers = {"Accept": "application/json"}
		response = requests.post(
			"https://github.com/login/oauth/access_token", data=data, headers=headers
		).json()
		frappe.db.set_value("Team", team, "github_access_token", response["access_token"])
	except Exception:
		log_error("Access Token Error", team=team, response=summarize_github_token_response(response))


def summarize_github_token_response(response):
	if not response:
		return None

	return {
		"error": response.get("error"),
		"error_description": response.get("error_description"),
		"error_uri": response.get("error_uri"),
		"has_access_token": bool(response.get("access_token")),
		"scope": response.get("scope"),
		"token_type": response.get("token_type"),
	}
