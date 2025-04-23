# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AgentUpdateServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		current_commit: DF.Data | None
		end: DF.Datetime | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rollbacked: DF.Check
		server: DF.Data
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Success", "Failure", "Skipped"]
	# end: auto-generated types

	pass
