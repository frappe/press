# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class MpesaRequestLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		data: DF.Code | None
		error: DF.Code | None
		integration_request_service: DF.Data | None
		is_remote_request: DF.Check
		output: DF.Code | None
		request_description: DF.Data | None
		request_headers: DF.Code | None
		request_id: DF.Data | None
		status: DF.Literal["", "Queued", "Authorized", "Completed", "Cancelled", "Failed"]
		url: DF.SmallText | None
	# end: auto-generated types

	def before_insert(self):
		self.validate_duplicate_request_id()

	def validate_duplicate_request_id(self):
		request_logs = frappe.get_all(
			"Mpesa Request Log",
			{
				"name": ("!=", self.name),
				"request_id": self.request_id,
				"status": "Completed",
				"integration_request_service": self.integration_request_service,
			},
			pluck="name",
		)
		if request_logs:
			frappe.throw(f"Request log already processed with this request id: {self.request_id}")
