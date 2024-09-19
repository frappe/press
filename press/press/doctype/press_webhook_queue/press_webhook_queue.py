# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
import requests
import json
from frappe.model.document import Document


class PressWebhookQueue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data: DF.SmallText
		event: DF.Link
		status: DF.Literal["Pending", "Sent", "Partially Sent", "Failed"]
		team: DF.Link
	# end: auto-generated types

	def send(self):
		if self.status == "Sent":
			return
		try:
			PressWebhookSelectedEvent = frappe.qb.DocType("Press Webhook Selected Event")
			PressWebhook = frappe.qb.DocType("Press Webhook")
			query = (
				frappe.qb.from_(PressWebhookSelectedEvent)
				.select(PressWebhook.name, PressWebhook.callback_url, PressWebhook.secret)
				.left_join(PressWebhook)
				.on(PressWebhookSelectedEvent.parent == PressWebhook.name)
				.where(PressWebhookSelectedEvent.event == self.event)
				.where(PressWebhook.team == self.team)
				.where(PressWebhook.enabled == 1)
			)
			records = query.run(as_dict=True)
			data = json.loads(self.data)
			payload = {
				"event": self.event,
				"data": data,
			}
			total = len(records)
			sent = 0
			for record in records:
				response = ""
				response_status_code = 0
				try:
					req = requests.post(
						record.callback_url,
						json=payload,
						headers={"X-Webhook-Secret": record.secret},
						timeout=5,
					)
					response = req.text or ""
					response_status_code = req.status_code
				except Exception as e:
					response = str(e)

				isSent = response_status_code >= 200 and response_status_code < 300
				if isSent:
					sent += 1

				frappe.get_doc(
					{
						"doctype": "Press Webhook Log",
						"webhook": record.name,
						"event": self.event,
						"status": "Sent" if isSent else "Failed",
						"request_payload": json.dumps(payload, default=str),
						"response_body": response,
						"response_status_code": response_status_code,
					}
				).insert(ignore_permissions=True)

			if total != 0 and sent == 0:
				self.status = "Failed"
			elif total == 0:
				self.status = "Sent"
			elif total != 0 and sent != total:
				self.status = "Partially Sent"
			elif total == sent:
				self.status = "Sent"
			self.save()
		except Exception as e:
			self.status = "Failed"
			self.save()


def process_webhook_queue():
	records = frappe.get_all(
		"Press Webhook Queue", filters={"status": "Pending"}, pluck="name"
	)
	for record in records:
		frappe.enqueue_doc(
			"Press Webhook Queue",
			record,
			method="send",
			queue="long",
			job_name=f"webhook_queue:{record}",
			deduplicate=True,
			now=True,
		)
