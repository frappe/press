# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AppReleaseApprovalCodeComments(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		comment: DF.SmallText
		commented_by: DF.Link
		filename: DF.SmallText
		line_number: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		time: DF.Datetime
	# end: auto-generated types
	pass
