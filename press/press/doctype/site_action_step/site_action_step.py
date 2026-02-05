# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SiteActionStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attempts: DF.Int
		duration: DF.Duration | None
		end: DF.Datetime | None
		method: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Scheduled", "Running", "Skipped", "Success", "Failure"]
		step: DF.Data
		step_type: DF.Literal["Preparation", "Main", "Cleanup"]
		traceback: DF.Text | None
		wait_for_completion: DF.Check
	# end: auto-generated types

	def validate(self):
		if self.is_async_step and self.wait_for_completion:
			frappe.throw("Cannot wait for completion on async kind of step")

	def get_steps(self):
		if self.reference_doctype and self.reference_name:
			reference_doc = frappe.get_doc(
				self.reference_doctype,
				self.reference_name,
			)
			# Check if the doc hsa get_steps method
			if hasattr(reference_doc, "get_steps"):
				return reference_doc.get_steps()

		# TODO: somehow have to add visibility of this stage
		return [
			{
				"name": self.name,
				"title": "",
				"status": self.status,
				"output": self.traceback if self.status == "Failure" else None,
				"stage": self.step,
			}
		]
