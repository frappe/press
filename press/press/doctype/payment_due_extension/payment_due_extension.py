# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class PaymentDueExtension(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		extension_date: DF.Date
		reason: DF.SmallText
		team: DF.Link
	# end: auto-generated types

	def validate(self):
		if self.extension_date < frappe.utils.today():
			frappe.throw("Extension date cannot be in the past")

	def before_insert(self):
		if frappe.db.exists(
			"Payment Due Extension",
			{"team": self.team, "docstatus": 1, "extension_date": (">=", frappe.utils.today())},
		):
			frappe.throw("An active Payment due extension record already exists for this team")

	def on_submit(self):
		frappe.db.set_value("Team", self.team, "extend_payment_due_suspension", 1)


def remove_payment_due_extension():
	extensions = frappe.get_all(
		"Payment Due Extension",
		{"docstatus": 1, "extension_date": ("<", frappe.utils.today())},
		pluck="team",
	)
	for team in extensions:
		frappe.db.set_value("Team", team, "extend_payment_due_suspension", 0)
		frappe.db.commit()
