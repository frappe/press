# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IncidentSite(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		current_http_status: DF.Data | None
		current_status: DF.Literal[
			"Online",
			"Timeout",
			"TLS Issue",
			"Unauthorized",
			"Down Bench",
			"Internal Error",
			"Suspended",
			"Site Not Found",
			"Unreachable",
			"Evaluating",
		]
		current_status_updated_on: DF.Datetime | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reported_http_status: DF.Data | None
		reported_status: DF.Literal[
			"Online",
			"Timeout",
			"TLS Issue",
			"Unauthorized",
			"Down Bench",
			"Internal Error",
			"Site Suspended",
			"Site Not Found",
			"Unreachable",
		]
		site: DF.Data
	# end: auto-generated types

	pass
