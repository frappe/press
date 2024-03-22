# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AnsibleConsoleOutput(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		duration: DF.Time | None
		exception: DF.Code | None
		exit_code: DF.Int
		host: DF.Data | None
		name: DF.Int | None
		output: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Data | None
	# end: auto-generated types

	pass
