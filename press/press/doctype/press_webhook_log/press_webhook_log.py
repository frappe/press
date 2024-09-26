# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import json

import frappe
import requests
from frappe.model.document import Document
from frappe.utils import add_to_date, now

from press.overrides import get_permission_query_conditions_for_doctype


class PressWebhookLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.press_webhook_attempt.press_webhook_attempt import PressWebhookAttempt

		attempts: DF.Table[PressWebhookAttempt]
		event: DF.Link
		next_retry_at: DF.Datetime | None
		request_payload: DF.JSON
		retries: DF.Int
		status: DF.Literal["Pending", "Queued", "Sent", "Partially Sent", "Failed"]
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		if not self.next_retry_at:
			self.next_retry_at = frappe.utils.now()

	def _send_webhook_call(self, webhook_name, payload, url, secret, save: bool = True) -> bool:
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
		except requests.exceptions.ConnectionError:
			response = "Failed to connect to the webhook endpoint"
		except requests.exceptions.SSLError:
			response = "SSL Error. Please check if SSL the certificate of the webhook is valid."
		except (requests.exceptions.Timeout, requests.exceptions.ConnectTimeout):
			response = "Request Timeout. Please check if the webhook is reachable."
		except Exception as e:
			response = str(e)

		sent = response_status_code >= 200 and response_status_code < 300

		self.append(
			"attempts",
			{
				"endpoint": url,
				"webhook": webhook_name,
				"status": "Sent" if sent else "Failed",
				"response_body": response,
				"response_status_code": response_status_code,
				"timestamp": frappe.utils.now(),
			},
		)
		if save:
			self.save()

		return sent

	def schedule_retry(self, save: True):
		self.retries = self.retries + 1
		self.next_retry_at = add_to_date(now(), minutes=2**self.retries)
		if save:
			self.save()

	def send(self):
		if len(self.attempts) == 0:
			self._process_webhook_call()
			return

		# Try failed attempts
		self._retry_failed_attempts()

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
			payload = json.loads(self.request_payload)
			total = len(webhooks)
			sent = 0
			for webhook in webhooks:
				isSent = self._send_webhook_call(
					webhook.name,
					payload,
					webhook.endpoint,
					webhook.secret,
					save=False,
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

	def _retry_failed_attempts(self):
		webhook_call_status = frappe._dict()
		for record in self.attempts:
			if record.status == "Failed" and webhook_call_status.get(record.webhook, "") != "Sent":
				webhook_call_status[record.webhook] = "Failed"
			if record.status == "Sent":
				webhook_call_status[record.webhook] = "Sent"

		# filter out webhooks that need to be retried
		webhooks_to_retry = [
			webhook for webhook in webhook_call_status if webhook_call_status[webhook] == "Failed"
		]

		sent = 0
		payload = json.loads(self.request_payload)

		for webhook in webhooks_to_retry:
			webhook_data = frappe.get_value(
				"Press Webhook", record.webhook, ["endpoint", "secret"], as_dict=True
			)
			is_sent = self._send_webhook_call(
				webhook,
				payload,
				webhook_data.endpoint,
				webhook_data.secret,
			)
			if is_sent:
				sent += 1

		if len(webhooks_to_retry) == 0 or sent == len(webhooks_to_retry):
			self.status = "Sent"
		elif (len(webhook_call_status) - len(webhooks_to_retry) > 0) or sent > 0:
			self.status = "Partially Sent"
			self.schedule_retry(save=False)
		else:
			self.status = "Failed"
			self.schedule_retry(save=False)

		self.save()


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Press Webhook Log")


def process():
	records = frappe.get_all(
		"Press Webhook Log",
		filters={
			"status": ["in", ["Pending", "Failed", "Partially Sent"]],
			"retries": ["<=", 3],
			"next_retry_at": ["<=", frappe.utils.now()],
		},
		pluck="name",
		limit=100,
	)
	# set status of these records to Queued
	frappe.db.set_value("Press Webhook Log", {"name": ("in", records)}, "status", "Queued")
	# enqueue these records
	for record in records:
		frappe.enqueue_doc(
			"Press Webhook Log",
			record,
			method="send",
			queue="long",
			job_id=f"press_webhook_log:{record}",
			deduplicate=True,
		)


def clean_logs_older_than_24_hours():
	names = frappe.get_all(
		"Press Webhook Log", filters={"creation": ["<", frappe.utils.add_days(None, -1)]}, pluck="name"
	)
	frappe.delete_doc("Press Webhook Log", names)
