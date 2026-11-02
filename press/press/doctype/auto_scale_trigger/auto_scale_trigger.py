# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AutoScaleTrigger(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Literal["Scale Up", "Scale Down"]
		metric: DF.Literal["CPU", "Memory"]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		threshold: DF.Float
	# end: auto-generated types

	pass
