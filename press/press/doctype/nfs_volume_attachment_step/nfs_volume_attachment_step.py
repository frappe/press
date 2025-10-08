# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class NFSVolumeAttachmentStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		job: DF.DynamicLink | None
		job_type: DF.Link | None
		method_name: DF.Data | None
		output: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
		step_name: DF.Data | None
	# end: auto-generated types

	pass
