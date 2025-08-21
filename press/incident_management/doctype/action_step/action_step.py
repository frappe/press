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

		is_taken: DF.Check
		method: DF.Data | None
		output: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
	# end: auto-generated types

	def before_save(self):
		try:
			target_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		except frappe.DoesNotExistError:
			frappe.throw(
				f"Invalid reference: {self.reference_doctype} {self.reference_name}",
				frappe.DoesNotExistError,
			)

		if not hasattr(target_doc, self.method):
			frappe.throw(
				f"Method '{self.method}' does not exist on document '{target_doc.name}'",
				frappe.ValidationError,
			)

	def after_insert(self):
		"""We execute the step immediately we need to ensure the long functions are in a queue."""
		target_doc = frappe.get_doc(self.reference_doctype, self.reference_name)
		self.output = getattr(target_doc, self.method)()
		self.is_taken = True
		self.save()
