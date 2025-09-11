# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Provider(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		cloud_provider: DF.Link
		region: DF.Link
		secret: DF.Password
		status: DF.Literal["Select", "Active", "Expired"]
	# end: auto-generated types

	pass
