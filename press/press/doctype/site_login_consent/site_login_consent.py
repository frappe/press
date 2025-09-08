# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from frappe.utils import now_datetime


class SiteLoginConsent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		approved_by: DF.Link | None
		approved_on: DF.Datetime | None
		approved_until: DF.Datetime | None
		reason: DF.Text
		requested_by: DF.Link
		site: DF.Link
	# end: auto-generated types
	pass

	@property
	def expired(self) -> bool:
		return self.approved_until < now_datetime()
