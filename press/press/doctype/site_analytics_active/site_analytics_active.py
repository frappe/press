# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SiteAnalyticsActive(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		email: DF.Data | None
		enabled: DF.Check
		full_name: DF.Data | None
		is_system_manager: DF.Check
		language: DF.Data | None
		last_active: DF.Datetime | None
		last_login: DF.Datetime | None
		name: DF.Int | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		time_zone: DF.Data | None
	# end: auto-generated types

	pass
