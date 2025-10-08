# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
import frappe.utils
from frappe.model.document import Document

from press.utils import get_current_team


class SupportAccess(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.support_access_resource.support_access_resource import SupportAccessResource

		access_allowed_till: DF.Datetime | None
		all_access: DF.Check
		allowed_for: DF.Literal["3", "6", "12", "24"]
		bench_ssh_access: DF.Check
		dashboard_access: DF.Check
		reason: DF.SmallText | None
		requested_by: DF.Link | None
		requested_team: DF.Link | None
		resources: DF.Table[SupportAccessResource]
		site_access: DF.Check
		status: DF.Literal["Pending", "Accepted", "Rejected"]
	# end: auto-generated types

	@property
	def access_expired(self):
		return bool(
			self.access_allowed_till
			and frappe.utils.get_datetime(self.access_allowed_till) < frappe.utils.now_datetime()
		)

	def before_validate(self):
		self.requested_by = self.requested_by or frappe.session.user
		self.requested_team = self.requested_team or get_current_team()
		self.set_expiry()

	def set_expiry(self):
		doc_before = self.get_doc_before_save()
		hours = frappe.utils.cint(self.allowed_for)
		if hours and doc_before and doc_before.status != self.status and self.status == "Accepted":
			self.access_allowed_till = frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=hours)

	def validate(self):
		self.validate_status_change()
		self.validate_expiry()

	def validate_status_change(self):
		doc_before = self.get_doc_before_save()
		if doc_before and doc_before.status != "Pending" and doc_before.status != self.status:
			frappe.throw("Status can only be changed if it is Pending")

	def validate_expiry(self):
		if self.access_expired:
			frappe.throw("Access expiry must be in the future")
		if self.status != "Accepted" and self.access_allowed_till:
			frappe.throw("Access expiry can only be set if access is accepted")
