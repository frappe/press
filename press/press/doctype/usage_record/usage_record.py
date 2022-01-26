# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from press.utils import log_error


class UsageRecord(Document):
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
