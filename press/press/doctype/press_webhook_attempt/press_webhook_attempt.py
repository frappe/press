# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class PressWebhookAttempt(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		endpoint: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		response_body: DF.SmallText | None
		response_status_code: DF.Data | None
		status: DF.Literal["Sent", "Failed"]
		timestamp: DF.Datetime
		webhook: DF.Link
	# end: auto-generated types


def has_permission(doc, ptype, user):
	if ptype != "read":
		return False
	return frappe.get_doc("Press Webhook", doc.webhook).has_permission("read", user)
