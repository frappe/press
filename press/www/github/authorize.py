# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import json
import frappe
import requests
from press.utils import log_error
from base64 import b64decode


def get_context(context):
	code = frappe.form_dict.code
	state = frappe.form_dict.state
	redirect_url = frappe.utils.get_url("/dashboard")
	if code and state:
		decoded_state = json.loads(b64decode(state).decode())
		team = decoded_state["team"]
		redirect_url = frappe.utils.get_url(decoded_state["url"])
		obtain_access_token(code, team)
		frappe.db.commit()
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
		log_error("Access Token Error", team=team, code=code, response=response)
