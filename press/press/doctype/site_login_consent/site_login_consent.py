# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import datetime

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from press.api.client import dashboard_whitelist


class SiteLoginConsent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		approved_by: DF.Link | None
		reason: DF.Text
		requested_by: DF.Link
		site: DF.Link
		status: DF.Literal["Pending", "Approved", "Rejected"]
		until: DF.Datetime | None
	# end: auto-generated types
	pass

	dashboard_fields = (
		"requested_by",
		"site",
		"status",
		"until",
	)

	@property
	def expired(self) -> bool:
		if not self.until or type(self.until) is str:
			return False
		return self.until < now_datetime()

	@dashboard_whitelist()
	def approve(self):
		if self.status != "Pending":
			frappe.throw("Only pending requests can be approved.")
		self.status = "Approved"
		self.approved_by = frappe.session.user
		self.until = now_datetime() + datetime.timedelta(hours=24)
		self.save()

	@dashboard_whitelist()
	def reject(self):
		if self.status != "Pending":
			frappe.throw("Only pending requests can be rejected.")
		self.status = "Rejected"
		self.save()
