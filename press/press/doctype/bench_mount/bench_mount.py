# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BenchMount(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		destination: DF.Data
		is_absolute_path: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		source: DF.Data
	# end: auto-generated types

	pass
