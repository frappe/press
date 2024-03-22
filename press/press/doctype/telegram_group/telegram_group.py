# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TelegramGroup(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.telegram_group_topic.telegram_group_topic import (
			TelegramGroupTopic,
		)

		chat_id: DF.Data
		token: DF.Data | None
		topics: DF.Table[TelegramGroupTopic]
	# end: auto-generated types

	pass
