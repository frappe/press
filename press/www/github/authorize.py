# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
import requests

from press.api.github import (
	InvalidGitHubOAuthState,
	decode_github_oauth_state,
	encode_github_oauth_state,
	get_github_authorize_url,
	get_github_callback_login_redirect,
)
from press.utils import get_valid_teams_for_user, log_error


def get_context(context):
	code = frappe.form_dict.code
	state = frappe.form_dict.state
	redirect_url = frappe.utils.get_url("/dashboard")

	if frappe.session.user == "Guest":
		frappe.flags.redirect_location = get_github_callback_login_redirect(code, state)
		raise frappe.Redirect

	if state and not code and not frappe.form_dict.error:
		# GitHub redirected back from a (re)installation without an OAuth code.
		# The token stored on the team may now be stale, so start user
		# authorization to exchange a fresh code for a new access token.
		start_user_authorization(state)

	if code and state:
		try:
			decoded_state = decode_github_oauth_state(state)
			team = decoded_state["team"]
			valid_teams = {team_doc["name"] for team_doc in get_valid_teams_for_user(frappe.session.user)}
			if team not in valid_teams:
				raise frappe.PermissionError("Not permitted to update this team's GitHub access token")

			redirect_url = frappe.utils.get_url(decoded_state["redirect_url"])
			obtain_access_token(code, team)
			frappe.db.commit()
		except Exception:
			log_error("GitHub OAuth Authorization Error")

	frappe.flags.redirect_location = redirect_url
	raise frappe.Redirect


def start_user_authorization(state):
	try:
		# Expiry is not checked here. The state is minted when the bench page
		# loads, and a user who leaves the page open before picking repositories
		# on GitHub comes back with a state well past GITHUB_OAUTH_STATE_MAX_AGE
		# — which used to end the install on /dashboard with no token. It is
		# still signed and bound to the logged-in user, and expiry is enforced on
		# the code-bearing leg, which runs on the state re-issued below.
		decoded_state = decode_github_oauth_state(state, check_expiry=False)
	except InvalidGitHubOAuthState:
		log_error("GitHub OAuth Authorization Error")
		return

	# Re-issue the state so the authorization leg gets a fresh validity window.
	fresh_state = encode_github_oauth_state(decoded_state["team"], decoded_state["redirect_url"])
	frappe.flags.redirect_location = get_github_authorize_url(fresh_state)
	raise frappe.Redirect


def obtain_access_token(code, team):
	response = None
	try:
		client_id = frappe.db.get_single_value("Press Settings", "github_app_client_id")
		client_secret = frappe.db.get_single_value("Press Settings", "github_app_client_secret")
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
