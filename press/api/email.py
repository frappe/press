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
from press.api.developer.marketplace import get_subscription_info
from press.api.site import site_config, update_config


class PlanExpiredError(Exception):
	http_status_code = 401


@frappe.whitelist(allow_guest=True)
def email_ping():
	return "pong"


def setup(site):
	"""
	set site config for overriding email account validations
	"""
	doc_exists = frappe.db.exists("Mail Setup", {"site": site})

	if doc_exists:
		doc = frappe.get_doc("Mail Setup", doc_exists)

		if not doc.is_complete:
			doc.is_complete = 1
			doc.save()

		return

	old_config = site_config(site)

	new_config = [
		{"key": "mail_login", "value": "example@gmail.com", "type": "String"},
		{"key": "mail_password", "value": "edjxok4jh7", "type": "String"},
		{"key": "mail_port", "value": 587, "type": "Number"},
		{"key": "mail_server", "value": "smtp.gmail.com", "type": "String"},
	]
	for row in old_config:
		new_config.append({"key": row.key, "value": row.value, "type": row.type})

	update_config(site, json.dumps(new_config))

	frappe.get_doc({"doctype": "Mail Setup", "site": site, "is_complete": 1}).insert(
		ignore_permissions=True
	)


@frappe.whitelist(allow_guest=True)
def get_analytics(**data):
	"""
	send data for a specific month
	"""
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


def validate_plan(secret_key):
	"""
	check if subscription is active on marketplace and valid
	#TODO: get activation date
	"""
	plan_label_map = {"Mail 25$": 10000, "Mail 5$": 2000, "Mail Free": 100}

	try:
		subscription = get_subscription_info(secret_key=secret_key)
	except Exception as e:
		frappe.throw(e)

	if subscription["status"] == "Active":
		# TODO: add a date filter(use start date from plan)
		count = frappe.db.count(
			"Mail Log",
			filters={
				"site": subscription["site"],
				"status": "delivered",
				"subscription_key": secret_key,
			},
		)
		if count < plan_label_map[subscription["plan"]]:
			return True
		else:
			frappe.throw(
				"Your plan for email delivery service has expired try upgrading it from, "
				f"https://frappecloud.com/dashboard/sites/{subscription['site']}/overview",
				PlanExpiredError,
			)

	return False


@frappe.whitelist(allow_guest=True)
def send_mime_mail(**data):
	"""
	send api request to mailgun
	"""
	files = frappe._dict(frappe.request.files)
	data = json.loads(data["data"])

	if validate_plan(data["sk_mail"]):
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
	"""
	log the webhook and forward it to site
	"""
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

	data = {"status": status, "message_id": message_id, "secret_key": secret_key}

	try:
		requests.post(
			f"https://{site}/api/method/email_delivery_service.controller.update_status",
			data=data,
		)
	except Exception as e:
		log_error("Mail App: Email status update error", data=e)
		return "Successful", 200

	return "Successful", 200
