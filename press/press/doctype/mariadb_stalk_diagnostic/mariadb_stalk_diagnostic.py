# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MariaDBStalkDiagnostic(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		output: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		type: DF.Data | None
	# end: auto-generated types

	pass
