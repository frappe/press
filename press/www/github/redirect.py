# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe
import requests
from press.utils import log_error


def get_context(context):
	if not frappe.db.get_single_value("Press Settings", "github_app_id"):
		code = frappe.form_dict.code
		response = None
		try:
			headers = {"Accept": "application/vnd.github.v3+json"}
			response = frappe._dict(
				requests.post(
					f"https://api.github.com/app-manifests/{code}/conversions", headers=headers,
				).json()
			)

			settings = frappe.get_doc("Press Settings", "Press Settings")
			settings.github_app_id = response.id
			settings.github_app_client_id = response.client_id
			settings.github_app_client_secret = response.client_secret
			settings.github_app_public_link = response.html_url
			settings.github_app_private_key = response.pem
			settings.github_webhook_secret = response.webhook_secret
			settings.save()
			frappe.db.commit()
		except Exception:
			log_error("GitHub App Creation Error", code=code, response=response)

	redirect_url = frappe.utils.get_url("/desk#Form/Press Settings")
	frappe.flags.redirect_location = redirect_url
	raise frappe.Redirect
