# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class SQLJobQuery(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		columns: DF.JSON | None
		duration: DF.Duration | None
		error_code: DF.Data | None
		error_message: DF.SmallText | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		profile: DF.JSON | None
		query: DF.SmallText
		result: DF.JSON | None
		row_count: DF.Int
		success: DF.Check
	# end: auto-generated types

	pass
