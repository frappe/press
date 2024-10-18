# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import calendar
import json
import secrets
from datetime import datetime

import frappe
import requests
from frappe.exceptions import OutgoingEmailError, TooManyRequestsError, ValidationError

from press.api.developer.marketplace import get_subscription_info
from press.api.site import site_config, update_config
from press.utils import log_error


class EmailLimitExceeded(TooManyRequestsError):
	pass


class EmailSendError(OutgoingEmailError):
	pass


class EmailConfigError(ValidationError):
	http_status_code = 400


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
		{"key": "mail_password", "value": "password", "type": "String"},
		{"key": "mail_port", "value": 587, "type": "Number"},
		{"key": "mail_server", "value": "smtp.gmail.com", "type": "String"},
	]
	for row in old_config:
		new_config.append({"key": row.key, "value": row.value, "type": row.type})

	update_config(site, json.dumps(new_config))

	frappe.get_doc({"doctype": "Mail Setup", "site": site, "is_complete": 1}).insert(ignore_permissions=True)


@frappe.whitelist(allow_guest=True)
def get_analytics(**data):
	"""
	send data for a specific month
	"""
	month = data.get("month")
	year = datetime.now().year
	last_day = calendar.monthrange(year, int(month))[1]
	status = data.get("status")
	site = data.get("site")
	subscription_key = data.get("key")

	for value in (site, subscription_key):
		if not value or not isinstance(value, str):
			frappe.throw("Invalid Request")

	return frappe.get_all(
		"Mail Log",
		filters={
			"site": site,
			"subscription_key": subscription_key,
			"status": ["like", f"%{status}%"],
			"date": ["between", [f"{month}-01-{year}", f"{month}-{last_day}-{year}"]],
		},
		fields=["date", "status", "message", "sender", "recipient"],
		order_by="date asc",
	)


def validate_plan(secret_key):
	"""
	check if subscription is active on marketplace and valid
	#TODO: get activation date
	"""

	# TODO: replace this with plan attributes
	plan_label_map = frappe.conf.email_plans

	if not secret_key:
		frappe.throw(
			"Secret key missing. Email Delivery Service seems to be improperly installed. Try uninstalling and reinstalling it.",
			EmailConfigError,
		)

	try:
		subscription = get_subscription_info(secret_key=secret_key)
	except Exception as e:
		frappe.throw(
			str(e)
			or "Something went wrong fetching subscription details of Email Delivery Service. Please raise a ticket at support.frappe.io",
			e,
		)

	if not subscription["enabled"]:
		frappe.throw(
			"Your subscription is not active. Try activating it from, "
			f"{frappe.utils.get_url()}/dashboard/sites/{subscription['site']}/overview",
			EmailConfigError,
		)

	# TODO: add a date filter(use start date from plan)
	first_day = str(frappe.utils.now_datetime().replace(day=1).date())
	count = frappe.db.count(
		"Mail Log",
		filters={
			"site": subscription["site"],
			"creation": (">=", first_day),
			"subscription_key": secret_key,
		},
	)
	if not count < plan_label_map[subscription["plan"]]:
		frappe.throw(
			"You have exceeded your quota for Email Delivery Service. Try upgrading it from, "
			f"{frappe.utils.get_url()}/dashboard/sites/{subscription['site']}/overview",
			EmailLimitExceeded,
		)


def check_spam(message: str):
	resp = requests.post(
		"https://frappemail.com/spamd/score",
		{"message": message},
	)
	if resp.status_code == 200:
		data = resp.json()
		if data["message"] > 3.5:
			frappe.throw(
				"This email was blocked as it was flagged as spam by our system. Please review the contents and try again.",
				EmailSendError,
			)
	else:
		log_error("Spam Detection: Error", data=resp.text, message=message)


@frappe.whitelist(allow_guest=True)
def send_mime_mail(**data):
	"""
	send api request to mailgun
	"""
	files = frappe._dict(frappe.request.files)
	data = json.loads(data["data"])

	validate_plan(data["sk_mail"])

	api_key, domain = frappe.db.get_value("Press Settings", None, ["mailgun_api_key", "root_domain"])

	message = files["mime"].read()
	check_spam(message.decode("utf-8"))

	resp = requests.post(
		f"https://api.mailgun.net/v3/{domain}/messages.mime",
		auth=("api", f"{api_key}"),
		data={"to": data["recipients"], "v:sk_mail": data["sk_mail"]},
		files={"message": message},
	)

	if resp.status_code == 200:
		return "Sending"  # Not really required as v14 and up automatically marks the email q as sent
	log_error("Email Delivery Service: Sending error", data=resp.text)
	frappe.throw(
		"Something went wrong with sending emails. Please try again later or raise a support ticket with support.frappe.io",
		EmailSendError,
	)
	return None


def is_valid_mailgun_event(event_data):
	if not event_data:
		return None

	if event_data.get("user-variables", {}).get("sk_mail") is None:
		# We don't know where to send this event
		# TOOD: Investigate why this is happening
		# Hint: Likely from other emails not sent via the email delivery app
		return None

	if "delivery-status" not in event_data:
		return None

	if "message" not in event_data["delivery-status"]:
		return None

	return True


@frappe.whitelist(allow_guest=True)
def event_log():
	"""
	log the webhook and forward it to site
	"""
	data = json.loads(frappe.request.data)
	event_data = data.get("event-data")

	if not is_valid_mailgun_event(event_data):
		return None

	try:
		secret_key = event_data["user-variables"]["sk_mail"]
		headers = event_data["message"]["headers"]
		if "message-id" not in headers:
			# We can't log this event without a message-id
			# TOOD: Investigate why this is happening
			return None
		message_id = headers["message-id"]
		site = (
			frappe.get_cached_value("Subscription", {"secret_key": secret_key}, "site")
			or message_id.split("@")[1]
		)
		status = event_data["event"]
		delivery_message = (
			event_data["delivery-status"]["message"] or event_data["delivery-status"]["description"]
		)
		frappe.get_doc(
			{
				"doctype": "Mail Log",
				"unique_token": secrets.token_hex(25),
				"message_id": message_id,
				"sender": headers["from"],
				"recipient": event_data.get("recipient") or headers.get("to"),
				"site": site,
				"status": event_data["event"],
				"subscription_key": secret_key,
				"message": delivery_message,
				"log": json.dumps(data),
			}
		).insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		log_error("Mail App: Event log error", data=data)
		raise

	data = {
		"status": status,
		"message_id": message_id,
		"delivery_message": delivery_message,
		"secret_key": secret_key,
	}

	try:
		host_name = frappe.db.get_value("Site", site, "host_name") or site
		requests.post(
			f"https://{host_name}/api/method/email_delivery_service.controller.update_status",
			data=data,
		)
	except Exception as e:
		log_error("Mail App: Email status update error", data=e)

	return "Successful", 200
