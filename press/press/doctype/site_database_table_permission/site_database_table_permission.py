# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SiteDatabaseTablePermission(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allow_all_columns: DF.Check
		mode: DF.Literal["read_only", "read_write"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		selected_columns: DF.SmallText
		table: DF.Data
	# end: auto-generated types

	pass
