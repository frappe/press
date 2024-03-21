# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CookiePreferenceLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		agreed_to_analytics_cookies: DF.Check
		agreed_to_functionality_cookies: DF.Check
		agreed_to_performance_cookies: DF.Check
		ip_address: DF.Data | None
	# end: auto-generated types

	pass
