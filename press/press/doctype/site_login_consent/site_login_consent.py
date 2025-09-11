# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class SiteLoginConsent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approved_by: DF.Link
		reason: DF.Text
		requested_by: DF.Link
		site: DF.Link
		status: DF.Literal["Pending", "Approved", "Rejected"]
		until: DF.Datetime
	# end: auto-generated types
	pass

	@property
	def expired(self) -> bool:
		return self.until < now_datetime()
