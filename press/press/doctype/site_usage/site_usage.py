# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class SiteUsage(Document):
	@staticmethod
	def clear_old_logs(days=60):
		table = frappe.qb.DocType("Site Usage")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))
