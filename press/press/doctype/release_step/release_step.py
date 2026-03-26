# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ReleaseStep(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.release_step_item.release_step_item import ReleaseStepItem

		release_group: DF.Link | None
		release_step_items: DF.Table[ReleaseStepItem]
		team: DF.Link
	# end: auto-generated types
	pass
