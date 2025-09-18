# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class InvestigationStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		is_likely_cause: DF.Check
		is_unable_to_investigate: DF.Check
		method: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		step_name: DF.SmallText | None
	# end: auto-generated types

	pass
