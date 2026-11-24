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
from press.press.doctype.github_installation.github_installation import (
	is_enabled_for_team,
	link_installations,
)
from press.utils import get_current_team, get_valid_teams_for_user, log_error


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

	if not state and frappe.form_dict.installation_id:
		start_authorization_for_current_team()

	if code and state:
		try:
			decoded_state = decode_github_oauth_state(state)
			team = decoded_state["team"]
			valid_teams = {team_doc["name"] for team_doc in get_valid_teams_for_user(frappe.session.user)}
			if team not in valid_teams:
				raise frappe.PermissionError("Not permitted to update this team's GitHub access token")

			redirect_url = frappe.utils.get_url(decoded_state["redirect_url"])
			if token := obtain_access_token(code, team):
				save_access_token(team, token)
			frappe.db.commit()
		except Exception:
			log_error("GitHub OAuth Authorization Error")
			frappe.db.commit()  # GET requests roll back, which would drop the error log

	frappe.flags.redirect_location = redirect_url
	raise frappe.Redirect


def start_user_authorization(state):
	try:
		decoded_state = decode_github_oauth_state(state)
	except InvalidGitHubOAuthState:
		log_error("GitHub OAuth Authorization Error")
		return

	# Re-issue the state so the authorization leg gets a fresh validity window.
	# The original was minted before the install wizard, which may already have
	# eaten most of GITHUB_OAUTH_STATE_MAX_AGE; reusing it risks the final
	# code-bearing callback failing decode and silently skipping the refresh.
	fresh_state = encode_github_oauth_state(decoded_state["team"], decoded_state["redirect_url"])
	frappe.flags.redirect_location = get_github_authorize_url(fresh_state)
	raise frappe.Redirect


def obtain_access_token(code, team) -> str | None:
	response = None
	try:
		client_id = frappe.db.get_single_value("Press Settings", "github_app_client_id")
		client_secret = frappe.db.get_single_value("Press Settings", "github_app_client_secret")
		data = {"client_id": client_id, "client_secret": client_secret, "code": code}
		headers = {"Accept": "application/json"}
		response = requests.post(
			"https://github.com/login/oauth/access_token", data=data, headers=headers
		).json()
		return response["access_token"]
	except Exception:
		log_error("Access Token Error", team=team, response=summarize_github_token_response(response))
		return None


def save_access_token(team: str, token: str):
	if is_enabled_for_team(team):
		link_installations(team, token)
	else:
		frappe.db.set_value("Team", team, "github_access_token", token)


def start_authorization_for_current_team():
	"""Link an install made on github.com, which comes back without our state."""
	team = get_current_team()
	if not is_enabled_for_team(team):
		return

	frappe.flags.redirect_location = get_github_authorize_url(encode_github_oauth_state(team))
	raise frappe.Redirect


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
