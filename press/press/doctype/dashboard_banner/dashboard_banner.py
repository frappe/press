# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DashboardBanner(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		message: DF.Data | None
		title: DF.Data | None
		type: DF.Literal["Info", "Success", "Error", "Warning"]
	# end: auto-generated types

	dashboard_fields = ["enabled", "message", "title", "type"]
