# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from press.utils import log_error


class TeamInvoice:
	def __init__(self, team, month, year):
		if isinstance(team, frappe.string_types):
			team = frappe.get_doc("Team", team)
		self.team = team
		self.month = month
		self.year = year

	def create(self, period_start=None):
		invoice = frappe.new_doc("Invoice")

		if not period_start:
			d = frappe.utils.datetime.datetime.now()
			# period starts on 1st of the month
			period_start = d.replace(day=1, month=self.month, year=self.year)

		invoice.update(
			{
				"team": self.team.name,
				"customer_name": frappe.utils.get_fullname(self.team.user),
				"customer_email": self.team.user,
				"currency": self.team.currency,
				"period_start": period_start,
			}
		)
		invoice.insert()
		return invoice

	def update_site_usage(self, ledger_entry):
		self.draft_invoice = self.get_draft_invoice()

		if not self.draft_invoice:
			log_error(
				"No draft invoice created to update site usage", ledger_entry=ledger_entry.name
			)
			return

		# return if this ledger_entry is already accounted for in an invoice
		if ledger_entry.invoice:
			return

		# return if this ledger entry does not match month-year of invoice
		ledger_entry_date = frappe.utils.getdate(ledger_entry.date)
		if not (
			self.draft_invoice.month == ledger_entry_date.month
			and self.draft_invoice.year == ledger_entry_date.year
		):
			return

		usage_row = None
		for usage in self.draft_invoice.site_usage:
			if usage.site == ledger_entry.site and usage.plan == ledger_entry.plan:
				usage_row = usage

		# if no row found, create a new row
		if not usage_row:
			self.draft_invoice.append(
				"site_usage",
				{"site": ledger_entry.site, "plan": ledger_entry.plan, "days_active": 1},
			)
		# if found, update row
		else:
			usage_row.days_active = (usage_row.days_active or 0) + 1

		self.draft_invoice.save()
		ledger_entry.db_set("invoice", self.draft_invoice.name)

	def get_draft_invoice(self):
		res = frappe.db.get_all(
			"Invoice",
			filters={
				"team": self.team.name,
				"status": "Draft",
				"month": self.month,
				"year": self.year,
			},
			limit=1,
		)
		return frappe.get_doc("Invoice", res[0].name) if res else None

	def get_invoice(self):
		res = frappe.db.get_all(
			"Invoice",
			filters={"team": self.team.name, "month": self.month, "year": self.year},
			limit=1,
		)
		return frappe.get_doc("Invoice", res[0].name) if res else None
