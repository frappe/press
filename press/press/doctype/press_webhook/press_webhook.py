# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import contextlib
import ipaddress
import json
from urllib.parse import urlparse
import frappe
from press.api.client import dashboard_whitelist
from press.overrides import get_permission_query_conditions_for_doctype
from press.utils import is_valid_hostname
import requests
from frappe.model.document import Document


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
	dashboard_fields = ["enabled", "endpoint", "events"]

	def validate(self):
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

	def validate_endpoint_url_format(self) -> dict:
		url = urlparse(self.endpoint)
		if not url.netloc:
			frappe.throw("Endpoint should be a valid url")

		# protocol should be http or https
		if url.scheme not in ["http", "https"]:
			frappe.throw("Endpoint should start with http:// or https://")

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

			try:
				url.port
			except ValueError:
				frappe.throw("Port no of the endpoint is invalid")

			# Endpoint can't be any local domain
			if not frappe.conf.developer_mode and (
				"localhost" in url.hostname or ".local" in url.hostname
			):
				frappe.throw("Endpoint can't be localhost or local domain")

	@dashboard_whitelist()
	def validate_endpoint(self) -> dict:
		response = ""
		response_status_code = 0
		payload = {"event": "Webhook Test", "data": {}}
		try:
			req = requests.post(
				self.endpoint,
				timeout=5,
				json=payload,
				headers={"X-Webhook-Secret": self.secret},
			)
			response = req.text or ""
			response_status_code = req.status_code
		except Exception as e:
			response = e.__str__()

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
	def delete(self):
		frappe.db.sql("delete from `tabPress Webhook Log` where webhook = %s", (self.name,))
		frappe.delete_doc("Press Webhook", self.name)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Site")
