# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document


class UsageRecord(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		currency: DF.Link | None
		date: DF.Date | None
		document_name: DF.DynamicLink | None
		document_type: DF.Link | None
		interval: DF.Data | None
		invoice: DF.Link | None
		payout: DF.Data | None
		plan: DF.DynamicLink | None
		plan_type: DF.Link | None
		remark: DF.SmallText | None
		site: DF.Link | None
		subscription: DF.Link | None
		team: DF.Link | None
		time: DF.Time | None
	# end: auto-generated types

	def validate(self):
		if not self.date:
			self.date = frappe.utils.today()

		if not self.time:
			self.time = frappe.utils.nowtime()

	def before_submit(self):
		self.validate_duplicate_usage_record()

	def on_submit(self):
		self.update_usage_in_invoice()

	def on_cancel(self):
		self.remove_usage_from_invoice()

	def update_usage_in_invoice(self):
		team = frappe.get_doc("Team", self.team)

		if team.parent_team:
			team = frappe.get_doc("Team", team.parent_team)

		if team.billing_team:
			team = frappe.get_doc("Team", team.billing_team)

		if team.free_account:
			return
		# Get a read lock on this invoice
		# We're going to update the invoice and we don't want any other process to update it
		invoice = team.get_upcoming_invoice(for_update=True)
		if not invoice:
			invoice = team.create_upcoming_invoice()

		invoice.add_usage_record(self)

	def remove_usage_from_invoice(self):
		team = frappe.get_doc("Team", self.team)
		invoice = team.get_upcoming_invoice()
		if invoice:
			invoice.remove_usage_record(self)

	def validate_duplicate_usage_record(self):
		usage_record = frappe.get_all(
			"Usage Record",
			{
				"name": ("!=", self.name),
				"team": self.team,
				"document_type": self.document_type,
				"document_name": self.document_name,
				"interval": self.interval,
				"date": self.date,
				"plan": self.plan,
				"docstatus": 1,
				"subscription": self.subscription,
				"amount": self.amount,
			},
			pluck="name",
		)

		if usage_record:
			frappe.throw(
				f"Usage Record {usage_record[0]} already exists for this document",
				frappe.DuplicateEntryError,
			)


def link_unlinked_usage_records():
	td = frappe.utils.today()
	fd = frappe.utils.get_first_day(td)
	ld = frappe.utils.get_last_day(td)
	free_teams = frappe.db.get_all("Team", {"free_account": 1}, pluck="name")

	usage_records = frappe.get_all(
		"Usage Record",
		filters={
			"invoice": ("is", "not set"),
			"date": ("between", (fd, ld)),
			"team": ("not in", free_teams),
			"docstatus": 1,
		},
		pluck="name",
		ignore_ifnull=True,
	)

	for usage_record in usage_records:
		try:
			frappe.get_doc("Usage Record", usage_record).update_usage_in_invoice()
		except Exception:
			frappe.log_error("Failed to Link UR to Invoice")


def on_doctype_update():
	frappe.db.add_index("Usage Record", ["subscription", "date"])
