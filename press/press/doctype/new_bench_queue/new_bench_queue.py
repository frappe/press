# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class NewBenchQueue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bench: DF.Link | None
		payload: DF.JSON
		status: DF.Literal["Queued", "Started", "Failure"]
	# end: auto-generated types
	pass
