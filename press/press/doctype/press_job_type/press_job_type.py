# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PressJobType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.press_job_type_step.press_job_type_step import (
			PressJobTypeStep,
		)

		steps: DF.Table[PressJobTypeStep]
	# end: auto-generated types

	pass
