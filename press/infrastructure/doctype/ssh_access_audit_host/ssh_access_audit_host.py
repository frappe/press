# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class SSHAccessAuditHost(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		host: DF.Data
		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal["Pending", "Completed", "Unreachable"]
		users: DF.Code | None
	# end: auto-generated types

	pass
