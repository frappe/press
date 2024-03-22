# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.utils import log_error


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
		invoice: DF.Data | None
		payout: DF.Data | None
		plan: DF.DynamicLink | None
		plan_type: DF.Link | None
		remark: DF.SmallText | None
		site: DF.Link | None
		subscription: DF.Data | None
		team: DF.Link | None
		time: DF.Time | None
	# end: auto-generated types

	def validate(self):
		if not self.date:
			self.date = frappe.utils.today()

		if not self.time:
			self.time = frappe.utils.nowtime()

	def on_submit(self):
		try:
			self.update_usage_in_invoice()
		except Exception:
			log_error(title="Usage Record Invoice Update Error", name=self.name)

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
		invoice = team.get_upcoming_invoice()
		if not invoice:
			invoice = team.create_upcoming_invoice()

		invoice.add_usage_record(self)

	def remove_usage_from_invoice(self):
		team = frappe.get_doc("Team", self.team)
		invoice = team.get_upcoming_invoice()
		if invoice:
			invoice.remove_usage_record(self)


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
		},
		pluck="name",
	)

	for usage_record in usage_records:
		try:
			frappe.get_doc("Usage Record", usage_record).update_usage_in_invoice()
		except Exception as e:
			frappe.log_error("Failed to Link UR to Invoice", data=e)


def on_doctype_update():
	frappe.db.add_index("Usage Record", ["subscription", "date"])
