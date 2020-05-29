# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt

from __future__ import unicode_literals
import frappe
import requests


def get_context(context):
	code = frappe.form_dict.code
	if code:
		obtain_access_token(code)
		frappe.db.commit()
	frappe.flags.redirect_location = "http://press.com:8080/dashboard/#/apps/new"
	raise frappe.Redirect


def obtain_access_token(code):
	client_id = frappe.db.get_single_value("Press Settings", "github_app_client_id")
	client_secret = frappe.db.get_single_value(
		"Press Settings", "github_app_client_secret"
	)
	data = {"client_id": client_id, "client_secret": client_secret, "code": code}
	headers = {"Accept": "application/json"}
	response = requests.post(
		"https://github.com/login/oauth/access_token", data=data, headers=headers,
	).json()
	team = frappe.get_doc("Team", frappe.session.user)
	team.github_access_token = response["access_token"]
	team.save()
