# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TelegramMessage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		group: DF.Data | None
		message: DF.Code
		parse_mode: DF.Literal["Markdown", "HTML"]
		priority: DF.Literal["High", "Medium", "Low"]
		status: DF.Literal["Queued", "Sent", "Error", "Cancelled", "Skipped"]
		topic: DF.Data | None
	# end: auto-generated types

	@staticmethod
	def enqueue(
		message: str,
	):
		"""Enqueue message for sending"""
		return frappe.get_doc(
			{
				"doctype": "Telegram Message",
				"message": message,
			}
		).insert(ignore_permissions=True)

	pass
