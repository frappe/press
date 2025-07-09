# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

from frappe.model.document import Document


class ProvisionPlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	if TYPE_CHECKING:
		from frappe.types import DF

		cluster: DF.Link
		error_log: DF.Code | None
		plan: DF.Code
		plan_name: DF.Link
		provider: DF.Data
		region: DF.Data
		status: DF.Literal["Select", "Pending", "Running", "Stopped", "Terminated"]
	# end: auto-generated types

	pass
