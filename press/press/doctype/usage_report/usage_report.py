# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class UsageReport(Document):
	def after_insert(self):
		self.create_ledger_entry()

	def create_ledger_entry(self):
		user = frappe.db.get_value("Site", self.site, "owner")
		entry = frappe.get_doc(
			{
				"doctype": "Credit Ledger Entry",
				"date": nowdate(),
				"user": user,
				"credit": 0,
				"debit": self.amount,
				"site": self.site,
				"usage_report": self.name,
			}
		).insert()
