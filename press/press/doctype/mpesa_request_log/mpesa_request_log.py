# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

# import frappe
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
		reference_docname: DF.DynamicLink | None
		reference_doctype: DF.Link | None
		request_description: DF.Data | None
		request_headers: DF.Code | None
		request_id: DF.Data | None
		status: DF.Literal["", "Queued", "Authorized", "Completed", "Cancelled", "Failed"]
		url: DF.SmallText | None
	# end: auto-generated types

	pass
