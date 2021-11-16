# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
import secrets
import json
import requests
from datetime import datetime


@frappe.whitelist(allow_guest=True)
def email_ping():
	return "pong"


def validate_plan(team, site):
	"""
	check if subscription exists and if it's active
	"""
	# ToDo: first_day should be the day subscription was enabled
	active = frappe.db.get_all(
		"QMail Subscription",
		pluck="emails",
		filters={"team": team, "site": site, "enabled": 1},
	)

	if active and len(active) == 1:
		date = datetime.today().date()
		first_day = date.strftime("%Y-%m-01")

		count = frappe.db.count(
			"QMail Log", filters={"site": site, "status": "delivered", "date": [">=", first_day]}
		)

		if count < int(active[0]):
			return True

	return False


def can_change_plan():
	# ToDo:
	# check unpaid invoices
	# check if card is added and have enough balance
	pass


@frappe.whitelist(allow_guest=True)
def change_plan(**data):
	can_change_plan()
	current_plan = frappe.db.get_all(
		"QMail Subscription",
		filters={"team": data["team"], "site": data["site"], "enabled": 1},
	)

	if current_plan:
		doc = frappe.get_doc("QMail Subscription", current_plan[0]["name"])
		doc.plan = data["plan"]
		doc.save(ignore_permissions=True)
		frappe.db.commit()
	else:
		frappe.get_doc(
			{
				"doctype": "QMail Subscription",
				"team": data["team"],
				"site": data["site"],
				"plan": data["plan"],
				"enabled": 1,
			}
		).insert(ignore_permissions=True)
	return "Successful", 200


@frappe.whitelist(allow_guest=True)
def create_subscription(**data):
	"""
	Testing: create subscription
	"""
	if data["passphrase"] == "xHupBrxg1pPvVXG5":
		frappe.get_doc(
			{
				"doctype": "QMail Subscription",
				"team": data["team"],
				"site": data["site"],
				"plan": "Free100",
				"enabled": 1,
			}
		).insert(ignore_permissions=True)

	return {"plan_name": "Free100", "emails": 100, "price": 0}


@frappe.whitelist(allow_guest=True)
def send_mail(**data):
	files = frappe._dict(frappe.request.files)
	data = json.loads(data["data"])

	if validate_plan(data["team"], data["site"]):
		api_key, domain = frappe.db.get_value(
			"Press Settings", None, ["mailgun_api_key", "root_domain"]
		)

		content = "html" if data["html"] else "text"

		attachments = []
		if files:
			for file_name, bin_data in files.items():
				attachments.append(("attachment", (file_name, bin_data)))

		requests.post(
			f"https://api.mailgun.net/v3/{domain}/messages",
			auth=("api", f"{api_key}"),
			files=attachments,
			data={
				"v:site_name": f"{data['site']}",
				"from": f"{data['sender']}",
				"to": data["recipient"],
				"cc": data["cc"],
				"bcc": data["bcc"],
				"subject": data["subject"],
				content: data["content"],
			},
		)

		return "Successful"
	else:
		return "Error"


@frappe.whitelist(allow_guest=True)
def event_log(**data):
	event_data = data["event-data"]
	headers = event_data["message"]["headers"]

	frappe.get_doc(
		{
			"doctype": "QMail Log",
			"unique_token": secrets.token_hex(25),
			"sender": headers["from"],
			"recipient": headers["to"],
			"subject": headers["subject"],
			"site": event_data["user-variables"]["site_name"],
			"status": event_data["event"],
			"log": event_data["event"],
		}
	).insert(ignore_permissions=True)

	return "Successful", 200
