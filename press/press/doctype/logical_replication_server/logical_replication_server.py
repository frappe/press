# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LogicalReplicationServer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		archived: DF.Check
		current_role: DF.Literal["Master", "Replica", "Hot Standby"]
		database_server: DF.Link
		new_role: DF.Literal["", "Master", "Replica", "Hot Standby", "Retired"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types

	pass
