# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import add_to_date, now


class PressWebhookQueue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.press_webhook_failed_call.press_webhook_failed_call import (
			PressWebhookFailedCall,
		)

		data: DF.SmallText
		event: DF.Link
		failed_webhook_calls: DF.Table[PressWebhookFailedCall]
		next_retry_at: DF.Datetime | None
		retries: DF.Int
		status: DF.Literal["Pending", "Queued", "Sent", "Partially Sent", "Failed"]
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		if not self.next_retry_at:
			self.next_retry_at = frappe.utils.now()

	def _send_webhook_call(self, webhook_name, payload, url, secret) -> bool:
		response = ""
		response_status_code = 0
		try:
			req = requests.post(
				url,
				json=payload,
				headers={"X-Webhook-Secret": secret},
				timeout=5,
			)
			response = req.text or ""
			response_status_code = req.status_code
		except Exception as e:
			response = str(e)

		sent = response_status_code >= 200 and response_status_code < 300

		if not sent:
			# Add failed webhook call to failed_webhook_calls if not already there
			is_exist = False
			for call in self.failed_webhook_calls:
				if call.webhook == webhook_name:
					is_exist = True
					break
			if not is_exist:
				self.append("failed_webhook_calls", {"webhook": webhook_name})

		frappe.get_doc(
			{
				"doctype": "Press Webhook Log",
				"webhook": webhook_name,
				"event": self.event,
				"endpoint": url,
				"status": "Sent" if sent else "Failed",
				"request_payload": json.dumps(payload, default=str),
				"response_body": response,
				"response_status_code": response_status_code,
			}
		).insert(ignore_permissions=True)
		return sent

	def schedule_retry(self, save: True):
		if self.status in ["Failed", "Partially Sent"]:
			self.retries = self.retries + 1
			self.next_retry_at = add_to_date(now(), minutes=2**self.retries)
			if save:
				self.save()

	def send(self):
		if self.status == "Sent":
			return
		if self.status in ["Failed", "Partially Sent"]:
			self._retry_failed_calls()
			return
		self._process_webhook_call()

	def _process_webhook_call(self):
		try:
			PressWebhookSelectedEvent = frappe.qb.DocType("Press Webhook Selected Event")
			PressWebhook = frappe.qb.DocType("Press Webhook")
			query = (
				frappe.qb.from_(PressWebhookSelectedEvent)
				.select(PressWebhook.name, PressWebhook.endpoint, PressWebhook.secret)
				.left_join(PressWebhook)
				.on(PressWebhookSelectedEvent.parent == PressWebhook.name)
				.where(PressWebhookSelectedEvent.event == self.event)
				.where(PressWebhook.team == self.team)
				.where(PressWebhook.enabled == 1)
			)
			webhooks = query.run(as_dict=True)
			data = json.loads(self.data)
			payload = {
				"event": self.event,
				"data": data,
			}
			total = len(webhooks)
			sent = 0
			for webhook in webhooks:
				isSent = self._send_webhook_call(
					webhook.name,
					payload,
					webhook.endpoint,
					webhook.secret,
				)
				if isSent:
					sent += 1

			if total == 0:
				self.status = "Sent"
			else:
				if sent == total:
					self.status = "Sent"
				elif sent != total and sent != 0:
					self.status = "Partially Sent"
				else:
					self.status = "Failed"
					self.schedule_retry(save=False)
		except Exception:
			self.status = "Failed"
			self.schedule_retry(save=False)

		self.save()

	def _retry_failed_calls(self):
		total = len(self.failed_webhook_calls)
		sent = 0
		successful_calls = []
		for record in self.failed_webhook_calls:
			webhook_data = frappe.get_value(
				"Press Webhook", record.webhook, ["endpoint", "secret"], as_dict=True
			)
			isSent = self._send_webhook_call(
				record.webhook,
				json.loads(self.data),
				webhook_data.endpoint,
				webhook_data.secret,
			)
			if isSent:
				sent += 1
				successful_calls.append(record)

		for call in successful_calls:
			self.remove(call)

		if total == 0 or total == sent:
			self.status = "Sent"
		else:
			self.schedule_retry(save=False)

		self.save()


def process_webhook_queue():
	records = frappe.get_all(
		"Press Webhook Queue",
		filters={
			"status": ["in", ["Pending", "Failed", "Partially Sent"]],
			"retries": ["<=", 3],
			"next_retry_at": ["<=", frappe.utils.now()],
		},
		pluck="name",
		limit=100,
	)
	# set status of these records to Queued
	frappe.db.set_value("Press Webhook Queue", {"name": ("in", records)}, "status", "Queued")
	# enqueue these records
	for record in records:
		frappe.enqueue_doc(
			"Press Webhook Queue",
			record,
			method="send",
			queue="long",
			job_id=f"webhook_queue:{record}",
			deduplicate=True,
		)
