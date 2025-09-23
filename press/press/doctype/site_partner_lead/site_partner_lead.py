# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SitePartnerLead(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Data | None
		country: DF.Link | None
		created_on: DF.Date | None
		currency: DF.Link | None
		domain: DF.Data | None
		email: DF.Data | None
		first_name: DF.Data | None
		frappe_lead: DF.Data | None
		last_name: DF.Data | None
		site: DF.Link | None
		team: DF.Link
		users: DF.Int
	# end: auto-generated types

	pass
