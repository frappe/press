# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from __future__ import annotations

from frappe.model.document import Document


class VirtualMachineMigrationStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		attempts: DF.Int
		duration: DF.Duration | None
		end: DF.Datetime | None
		method: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		start: DF.Datetime | None
		status: DF.Literal["Pending", "Running", "Skipped", "Success", "Failure"]
		step: DF.Data
		traceback: DF.Code | None
		wait_for_completion: DF.Check
	# end: auto-generated types

	pass
