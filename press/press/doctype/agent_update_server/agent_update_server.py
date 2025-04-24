# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class AgentUpdateServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		current_commit: DF.Data | None
		end: DF.Datetime | None
		is_rollback_possible: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rollbacked: DF.Check
		server: DF.DynamicLink
		server_type: DF.Literal["Server", "Database Server", "Proxy Server"]
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Skipped"]
	# end: auto-generated types

	pass
