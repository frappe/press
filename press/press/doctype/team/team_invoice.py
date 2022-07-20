# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from press.utils import log_error
from frappe.utils import getdate


class TeamInvoice:
	def __init__(self, team, month, year):
		if isinstance(team, frappe.string_types):
			team = frappe.get_doc("Team", team)
		self.team = team
		self.month = month
		self.year = year

	def create(self, period_start=None):
		invoice = frappe.new_doc("Invoice")
		invoice.update(
			{
				"team": self.team.name,
				"period_start": period_start,
				"month": self.month,
				"year": self.year,
			}
		)
		invoice.insert()
		return invoice

	def update_site_usage(self, ledger_entry):
		self.get_draft_invoice()

		if not self.draft_invoice:
			log_error(
				"No draft invoice created to update site usage", ledger_entry=ledger_entry.name
			)
			return

		# return if this ledger_entry is already accounted for in an invoice
		if ledger_entry.invoice:
			return

		# return if this ledger_entry usage is not supposed to be billed
		if ledger_entry.free_usage:
			return

		# return if this ledger entry does not fall inside period of invoice
		ledger_entry_date = getdate(ledger_entry.date)
		start = getdate(self.draft_invoice.period_start)
		end = getdate(self.draft_invoice.period_end)
		if not (start <= ledger_entry_date <= end):
			return
		self.update_ledger_entry_in_invoice(ledger_entry, self.draft_invoice)

	def remove_ledger_entry_from_invoice(self, ledger_entry, invoice):
		usage_row = None
		for usage in invoice.site_usage:
			if usage.site == ledger_entry.site and usage.plan == ledger_entry.plan:
				usage_row = usage

		if usage_row and usage_row.days_active > 0:
			usage_row.days_active = usage_row.days_active - 1

		invoice.save()
		ledger_entry.db_set("invoice", "")

	def update_ledger_entry_in_invoice(self, ledger_entry, invoice):
		usage_row = None
		for usage in invoice.site_usage:
			if usage.site == ledger_entry.site and usage.plan == ledger_entry.plan:
				usage_row = usage

		# if no row found, create a new row
		if not usage_row:
			invoice.append(
				"site_usage",
				{"site": ledger_entry.site, "plan": ledger_entry.plan, "days_active": 1},
			)
		# if found, update row
		else:
			usage_row.days_active = (usage_row.days_active or 0) + 1

		invoice.save()
		ledger_entry.db_set("invoice", invoice.name)

	def get_draft_invoice(self):
		if hasattr(self, "draft_invoice"):
			return self.draft_invoice

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
		self.draft_invoice = frappe.get_doc("Invoice", res[0].name) if res else None
		return self.draft_invoice

	def get_invoice(self):
		res = frappe.db.get_all(
			"Invoice",
			filters={"team": self.team.name, "month": self.month, "year": self.year},
			limit=1,
		)
		return frappe.get_doc("Invoice", res[0].name) if res else None
