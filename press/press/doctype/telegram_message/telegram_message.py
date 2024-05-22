# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import traceback

import frappe
from frappe.model.document import Document
from press.telegram_utils import Telegram
from telegram.error import NetworkError


class TelegramMessage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		error: DF.Code | None
		group: DF.Data | None
		message: DF.Code
		parse_mode: DF.Literal["Markdown", "HTML"]
		priority: DF.Literal["High", "Medium", "Low"]
		retry_count: DF.Int
		topic: DF.Data | None
	# end: auto-generated types

	def send(self):
		try:
			telegram = Telegram()
			telegram.send(self.message)
			self.status = "Sent"
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
		priority: str = "Medium",
	):
		"""Enqueue message for sending"""
		return frappe.get_doc(
			{
				"doctype": "Telegram Message",
				"message": message,
				"priority": priority,
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

	while message := TelegramMessage.get_one():
		try:
			message.send()
			return
		except Exception:
			# Try next message
			pass
