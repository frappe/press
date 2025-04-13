# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from __future__ import annotations

# import frappe
from frappe.model.document import Document


class PhysicalRestorationTestResult(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		db_size_mb: DF.Int
		duration: DF.Duration | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		restore_record: DF.Link
		site: DF.Link
		status: DF.Literal["Pending", "Running", "Success", "Failure"]
	# end: auto-generated types

	pass
