# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.overrides import get_permission_query_conditions_for_doctype


class PressWebhookLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		endpoint: DF.Data
		event: DF.Link
		request_payload: DF.SmallText
		response_body: DF.SmallText | None
		response_status_code: DF.Data | None
		status: DF.Literal["Sent", "Failed"]
		team: DF.Link | None
		webhook: DF.Link
	# end: auto-generated types

	DOCTYPE = "Press Webhook Log"
	dashboard_fields = (
		"webhook",
		"event",
		"status",
		"endpoint",
		"request_payload",
		"response_body",
		"response_status_code",
		"creation",
	)


get_permission_query_conditions = get_permission_query_conditions_for_doctype("Press Webhook Log")


def clean_logs_older_than_24_hours():
	frappe.db.sql(
		"""
		DELETE FROM `tabPress Webhook Log`
		WHERE creation < NOW() - INTERVAL 24 HOUR
		"""
	)
