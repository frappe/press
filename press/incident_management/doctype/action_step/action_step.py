# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ActionStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attempt: DF.Int
		is_waiting: DF.Check
		job: DF.DynamicLink | None
		job_type: DF.Link | None
		max_attempt: DF.Int
		method_name: DF.Data | None
		output: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		step_name: DF.Data | None
	# end: auto-generated types


def on_doctype_update():
	"""Add index on parent and idx fields for faster ordered action step lookup
	https://dev.mysql.com/doc/refman/8.4/en/order-by-optimization.html#order-by-index-use
	"""
	frappe.db.add_index("Action Step", ["parent", "idx"])
