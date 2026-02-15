# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

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
