# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import traceback

import frappe
from frappe.model.document import Document
from press.telegram_utils import Telegram
from telegram.error import NetworkError, RetryAfter


class TelegramMessage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		error: DF.Code | None
		group: DF.Data | None
		message: DF.Code
		priority: DF.Literal["High", "Medium", "Low"]
		retry_count: DF.Int
		status: DF.Literal["Queued", "Sent", "Error"]
		topic: DF.Data | None
	# end: auto-generated types

	def send(self):
		try:
			telegram = Telegram(self.topic, self.group)
			if not self.group:
				self.group = telegram.group
			if not self.topic:
				self.topic = telegram.topic
			telegram.send(self.message, reraise=True)
			self.status = "Sent"
		except RetryAfter:
			# Raise an exception that will be caught by the scheduler
			# Try again after some time
			raise
		except NetworkError:
			# Try again. Not more than 5 times
			self.retry_count += 1
			self.error = traceback.format_exc()
			if self.retry_count >= 5:
				self.status = "Error"
			raise
		except Exception:
			# It's unlinkely that this error will be resolved by retrying
			# Fail immediately
			self.error = traceback.format_exc()
			self.status = "Error"
			raise
		finally:
			self.save()

	@staticmethod
	def enqueue(
		message: str,
		topic: str | None = None,
		group: str | None = None,
		priority: str = "Medium",
	):
		"""Enqueue message for sending"""
		return frappe.get_doc(
			{
				"doctype": "Telegram Message",
				"message": message,
				"priority": priority,
				"topic": topic,
				"group": group,
			}
		).insert(ignore_permissions=True)

	@staticmethod
	def get_one() -> "TelegramMessage | None":
		first = frappe.get_all(
			"Telegram Message",
			filters={"status": "Queued"},
			order_by="FIELD(priority, 'High', 'Medium', 'Low'), creation ASC",
			limit=1,
			pluck="name",
		)
		if first:
			return frappe.get_doc("Telegram Message", first[0])

	@staticmethod
	def send_one() -> None:
		message = TelegramMessage.get_one()
		if message:
			return message.send()


def send_telegram_message():
	"""Send one queued telegram message"""

	# Go through the queue till either of these things happen
	# 1. There are no more queued messages
	# 2. We successfully send a message
	# 3. Telegram asks us to stop (RetryAfter)
	# 4. We encounter an error that is not recoverable by retrying
	# (attempt 5 retries and remove the message from queue)
	while message := TelegramMessage.get_one():
		try:
			message.send()
			return
		except RetryAfter:
			# Retry in the next invocation
			return
		except Exception:
			# Try next message
			pass
