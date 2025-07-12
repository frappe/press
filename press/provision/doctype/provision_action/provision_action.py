# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ProvisionAction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Data
		action_output: DF.Code | None
		error_log: DF.Code | None
		output: DF.Code | None
		region: DF.Link
		stack: DF.Data
	# end: auto-generated types

	pass
