# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import secrets
import json
import requests
import calendar
from datetime import datetime

import frappe
from press.utils import log_error


@frappe.whitelist(allow_guest=True)
def email_ping():
	return "pong"


@frappe.whitelist(allow_guest=True)
def setup(**data):
	"""Set default keys for overriding email account validations"""
	if data["key"] == "fcmailfree100":
		site = frappe.get_doc("Site", data["site"])
		frappe.set_user(site.team)

		config = [
			{"mail_login": "example@email.com"},
			{"mail_password": "eDwuygx2j"},
			{"mail_port": 587},
			{"mail_server": "smtp.gmail.com"},
		]

		for row in config:
			site.update_site_config(row)
	else:
		log_error("Mail App: Invalid request key", data=data)

	return


@frappe.whitelist(allow_guest=True)
def get_analytics(**data):
	"""send data for a specific month"""
	month = data["month"]
	year = datetime.now().year
	last_day = calendar.monthrange(year, int(month))[1]
	status = data["status"]

	result = frappe.get_all(
		"Mail Log",
		filters={
			"site": data["site"],
			"subscription_key": data["key"],
			"status": ["like", f"%{status}%"],
			"date": ["between", [f"{month}-01-{year}", f"{month}-{last_day}-{year}"]],
		},
		fields=["date", "status", "message", "sender", "recipient"],
		order_by="date asc",
	)

	return result


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
			"site": site,
			"status": event_data["event"],
			"subscription_key": secret_key,
			"message": event_data["delivery-status"]["message"]
			or event_data["delivery-status"]["description"],
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
