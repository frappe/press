# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
import secrets
import json
import requests
from press.utils import log_error


@frappe.whitelist(allow_guest=True)
def email_ping():
	return "pong"


@frappe.whitelist(allow_guest=True)
def setup(**data):
	if data["key"] == "fcmailfree100":
		email, password = frappe.db.get_value(
			"Press Settings", None, ["default_outgoing_id", "default_outgoing_pass"]
		)
		return {
			"id": email,
			"pass": password,
		}
	return {}


def validate_plan(secret_key, site):
	"""
	check if subscription is active on marketplace and get activation date
	"""
	# ToDo: verify this key and validate plan from marketplace
	if secret_key == "fcmailfree100":
		count = frappe.db.count("Mail Log", filters={"site": site, "status": "delivered"})
		print(count)
		if count < 100:
			return True
	elif secret_key == "fcmailfrappeteam$1152":
		return True

	return False


@frappe.whitelist(allow_guest=True)
def send_mime_mail(**data):
	files = frappe._dict(frappe.request.files)
	data = json.loads(data["data"])

	if validate_plan(data["sk_mail"], data["site"]):
		api_key, domain = frappe.db.get_value(
			"Press Settings", None, ["mailgun_api_key", "root_domain"]
		)

		resp = requests.post(
			f"https://api.mailgun.net/v3/{domain}/messages.mime",
			auth=("api", f"{api_key}"),
			data={"to": data["recipients"], "v:sk_mail": data["sk_mail"]},
			files={"message": files["mime"].read()},
		)

		if resp.status_code == 200:
			return "Sending"

	return "Error"


@frappe.whitelist(allow_guest=True)
def event_log(**data):
	event_data = data["event-data"]
	headers = event_data["message"]["headers"]
	message_id = headers["message-id"]
	site = message_id.split("@")[1]
	status = event_data["event"]
	secret_key = event_data["user-variables"]["sk_mail"]

	frappe.get_doc(
		{
			"doctype": "Mail Log",
			"unique_token": secrets.token_hex(25),
			"message_id": message_id,
			"sender": headers["from"],
			"recipient": headers["to"],
			"subject": headers["subject"],
			"site": site,
			"status": event_data["event"],
			"subscription_key": secret_key,
			"log": json.dumps(data),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	data = {"status": status, "message_id": message_id}

	try:
		requests.post(
			f"https://{site}/api/method/mail.mail.doctype.mail_settings.mail_settings.update_status",
			data=data,
		)
	except Exception as e:
		log_error("Mail App: Email status update error", data=e)
		return "Successful", 200

	return "Successful", 200
