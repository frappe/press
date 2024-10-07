# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import contextlib
import ipaddress
import json
from urllib.parse import urlparse

import frappe
import frappe.query_builder
import frappe.query_builder.functions
import requests
from frappe.model.document import Document

from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import is_valid_hostname


class PressWebhook(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.press_webhook_selected_event.press_webhook_selected_event import (
			PressWebhookSelectedEvent,
		)

		enabled: DF.Check
		endpoint: DF.Data
		events: DF.Table[PressWebhookSelectedEvent]
		secret: DF.Data
		team: DF.Link
	# end: auto-generated types

	DOCTYPE = "Press Webhook"
	dashboard_fields = ("enabled", "endpoint", "events")

	def validate(self):
		# maximum 5 webhooks per team
		if self.is_new() and frappe.db.count("Press Webhook", {"team": self.team}) > 5:
			frappe.throw("You have reached the maximum number of webhooks per team")

		if self.has_value_changed("endpoint"):
			self.enabled = 0
		# should have atleast one event selected
		if not self.events:
			frappe.throw("At least one event should be selected")
		# validate endpoint url format
		self.validate_endpoint_url_format()
		# check for duplicate webhooks
		webhooks = frappe.get_all(
			"Press Webhook",
			filters={"team": self.team, "endpoint": self.endpoint, "name": ("!=", self.name)},
			pluck="name",
		)
		if len(webhooks) != 0:
			frappe.throw("You have already added webhook for this endpoint")

	def validate_endpoint_url_format(self):
		url = urlparse(self.endpoint)
		if not url.netloc:
			frappe.throw("Endpoint should be a valid url")

		# protocol should be http or https
		if url.scheme not in ["http", "https"]:
			frappe.throw("Endpoint should start with http:// or https://")

		# dont allow query params
		if url.query:
			frappe.throw("Endpoint should not have query params")

		isIPAddress = False
		# If endpoint target is ip address, it should be a public ip address
		with contextlib.suppress(ValueError):
			ip = ipaddress.ip_address(url.hostname)
			isIPAddress = True
			if not ip.is_global:
				frappe.throw("Endpoint address should be a public ip or domain")

		if not isIPAddress:
			# domain should be a fqdn
			if not is_valid_hostname(url.hostname):
				frappe.throw("Endpoint address should be a valid domain")

			# Endpoint can't be any local domain
			if not frappe.conf.developer_mode and ("localhost" in url.hostname or ".local" in url.hostname):
				frappe.throw("Endpoint can't be localhost or local domain")

	@dashboard_whitelist()
	def validate_endpoint(self) -> dict:
		response = ""
		response_status_code = 0
		payload = {"event": "Webhook Validate", "data": {}}
		try:
			req = requests.post(
				self.endpoint,
				timeout=5,
				json=payload,
				headers={"X-Webhook-Secret": self.secret},
			)
			response = req.text or ""
			response_status_code = req.status_code
		except requests.exceptions.ConnectionError:
			response = "Failed to connect to the webhook endpoint"
		except requests.exceptions.SSLError:
			response = "SSL Error. Please check if SSL the certificate of the webhook is valid."
		except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout):
			response = "Request Timeout. Please check if the webhook is reachable."
		except Exception as e:
			response = str(e)

		return frappe._dict(
			{
				"success": response_status_code >= 200 and response_status_code < 300,
				"request": json.dumps(payload, indent=2),
				"response": response,
				"response_status_code": response_status_code,
			}
		)

	@dashboard_whitelist()
	def activate(self):
		result = self.validate_endpoint()
		if result.get("success"):
			self.enabled = 1
			self.save()
			frappe.msgprint("Webhook activated successfully")
		else:
			message = f"<b>Status Code -</b> {result.response_status_code}</br><b>Response -</b></br>{result.response}"
			frappe.throw(title="Webhook endpoint is invalid", msg=message)

	@dashboard_whitelist()
	def disable(self):
		self.enabled = False
		self.save()

	@dashboard_whitelist()
	def disable_and_notify(self):
		self.disable()
		email = frappe.db.get_value("Team", self.team, "user")
		if not email:
			return
		if frappe.conf.developer_mode:
			print(f"Emailing {email}")
			print(f"{self.name} webhook has been disabled")
			return

		frappe.sendmail(
			recipients=email,
			subject="Important: Your Configured Webhook on Frappe Cloud is disabled",
			template="press_webhook_disabled",
			args={"endpoint": self.endpoint},
			now=True,
		)

	@dashboard_whitelist()
	def delete(self):
		frappe.db.sql("delete from `tabPress Webhook Attempt` where webhook = %s", (self.name,))
		frappe.delete_doc("Press Webhook", self.name)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site")


def auto_disable_high_delivery_failure_webhooks():
	# In past hour, if 70% of webhook deliveries has failed, disable the webhook and notify the user
	data = frappe.db.sql(
		"""
SELECT `endpoint`
FROM `tabPress Webhook Attempt`
WHERE `creation` >= NOW() - INTERVAL 1 HOUR
GROUP BY `endpoint`
HAVING (COUNT(CASE WHEN `status` = 'Failed' THEN 1 END) / COUNT(*)) * 100 > 70;
""",
		as_dict=True,
	)
	endpoints = [row.endpoint for row in data]
	doc_names = frappe.get_all("Press Webhook", filters={"endpoint": ("in", endpoints)}, pluck="name")
	for doc_name in doc_names:
		doc = frappe.get_doc("Press Webhook", doc_name)
		doc.disable_and_notify()
