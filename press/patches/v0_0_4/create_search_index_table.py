# -*- coding: utf-8 -*-
# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	if "__press_search" not in frappe.db.get_tables():
		frappe.db.sql(
			"""create table __press_search(
				doctype varchar({0}),
				title varchar({0}),
				route varchar({0}),
				team varchar({0}),
				name varchar({0}),
				fulltext (title),
				unique `doctype_title` (doctype, title))""".format(
				frappe.db.VARCHAR_LEN
			)
		)
