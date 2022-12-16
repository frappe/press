# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now


def execute():

	table = frappe.qb.DocType("Site Usage")
	frappe.db.delete(table, filters=(table.creation < (Now() - Interval(days=90))))
