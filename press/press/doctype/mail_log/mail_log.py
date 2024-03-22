# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MailLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		date: DF.Date | None
		log: DF.Code | None
		message: DF.Data | None
		message_id: DF.Data | None
		recipient: DF.Data | None
		sender: DF.Data | None
		site: DF.Data | None
		status: DF.Data | None
		subscription_key: DF.Data | None
		unique_token: DF.Data | None
	# end: auto-generated types

	pass
