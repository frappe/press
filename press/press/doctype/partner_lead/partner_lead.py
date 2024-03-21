# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PartnerLead(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		frappe_lead: DF.Data | None
		site: DF.Link | None
		team: DF.Link
	# end: auto-generated types

	pass
