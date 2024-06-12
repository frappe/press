# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class AgentRequestFailure(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		error: DF.Code
		failure_count: DF.Int
		server: DF.DynamicLink
		server_type: DF.Link
		traceback: DF.Code
	# end: auto-generated types

	pass
