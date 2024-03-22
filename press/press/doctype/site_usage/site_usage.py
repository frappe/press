# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


class SiteUsage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		backups: DF.Int
		database: DF.Int
		database_free: DF.Int
		database_free_tables: DF.Code | None
		private: DF.Int
		public: DF.Int
		site: DF.Link | None
	# end: auto-generated types

	@staticmethod
	def clear_old_logs(days=60):
		table = frappe.qb.DocType("Site Usage")
		frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=days))))
