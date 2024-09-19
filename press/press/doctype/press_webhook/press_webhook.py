# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
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

		callback_url: DF.Data
		enabled: DF.Check
		events: DF.Table[PressWebhookSelectedEvent]
		secret: DF.Data | None
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		if self.has_value_changed("callback_url"):
			self.enabled = 0

	def check_callback_url(self) -> dict:
		response = ""
		response_status_code = 0
		try:
			req = requests.post(
				self.callback_url,
				timeout=5,
				json={"event": "Webhook Test", "data": {}},
				headers={"X-Webhook-Secret": self.secret},
			)
			response = req.text or ""
			response_status_code = req.status_code
		except Exception as e:
			response = e.__str__()

		return frappe._dict(
			{
				"success": response_status_code >= 200 and response_status_code < 300,
				"response": response,
				"response_status_code": response_status_code,
			}
		)

	@frappe.whitelist()
	def activate(self):
		result = self.check_callback_url()
		if result.get("success"):
			self.enabled = 1
			self.save()
			frappe.msgprint("Webhook activated successfully")
		else:
			message = f"<b>Status Code -</b> {result.response_status_code}</br><b>Response -</b></br>{result.response}"
			frappe.throw(title="Webhook endpoint is invalid", msg=message)
