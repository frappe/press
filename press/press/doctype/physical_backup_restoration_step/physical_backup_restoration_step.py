# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe.model.document import Document


class PhysicalBackupRestorationStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attempts: DF.Int
		duration: DF.Duration | None
		end: DF.Datetime | None
		is_async: DF.Check
		is_cleanup_step: DF.Check
		method: DF.Data
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Scheduled", "Running", "Skipped", "Success", "Failure"]
		step: DF.Data
		traceback: DF.Code | None
		wait_for_completion: DF.Check
	# end: auto-generated types

	def validate(self):
		if self.is_async and self.wait_for_completion:
			frappe.throw("Cannot wait for completion on async kind of step")
