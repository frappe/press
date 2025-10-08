# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
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
		access_expired: DF.Check
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

	def before_validate(self):
		self.requested_by = self.requested_by or frappe.session.user
		self.requested_team = self.requested_team or get_current_team()

	def validate(self):
		self.validate_expiry()

	def validate_expiry(self):
		if self.access_allowed_till and self.access_allowed_till < frappe.utils.now_datetime():
			frappe.throw("Access expiry must be in the future")
		if self.status != "Accepted" and self.access_allowed_till:
			frappe.throw("Access expiry can only be set if access is accepted")


def expire_support_access():
	expired_access = frappe.get_all(
		"Support Access",
		{
			"access_expired": 0,
			"access_allowed_till": ("<", frappe.utils.now_datetime()),
			"status": "Accepted",
		},
		pluck="name",
	)

	for access in expired_access:
		frappe.db.set_value("Support Access", access, "access_expired", 1)
