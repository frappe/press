# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class SupportAccess(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from press.press.doctype.resources.resources import Resources

		access_allowed_till: DF.Datetime | None
		access_expired: DF.Check
		all_access: DF.Check
		allowed_for: DF.Literal["3", "6", "12", "24"]
		bench_ssh_access: DF.Check
		dashboard_access: DF.Check
		reason: DF.SmallText | None
		requested_by: DF.Link | None
		requested_for: DF.Link | None
		resources: DF.Table[Resources]
		site_access: DF.Check
		status: DF.Literal["Pending", "Accepted", "Rejected"]
	# end: auto-generated types

	def before_insert(self):
		if self.all_access:
			self.bench_ssh_access = 1
			self.dashboard_access = 1

	@frappe.whitelist()
	def accept_access(self):
		self.status = "Accepted"
		self.access_allowed_till = frappe.utils.add_to_date(
			frappe.utils.getdate(), hours=cint(self.allowed_for)
		)
		self.save()

	@frappe.whitelist()
	def reject_access(self):
		self.status = "Rejected"
		self.access_expired = 1
		self.save()


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
