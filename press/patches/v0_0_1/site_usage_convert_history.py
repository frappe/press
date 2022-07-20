# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from math import ceil

import frappe
from frappe.utils import cint


def execute():
	doctype = "Site Usage"
	frappe.reload_doctype(doctype)
	scheme_before = frappe.db.auto_commit_on_many_writes
	frappe.db.auto_commit_on_many_writes = True
	records = frappe.get_all(doctype, pluck="name")
	total = len(records)

	for current, record in enumerate(records):
		print(f"Updated {current} of {total}", end="\r")

		fields = ["backups", "database", "public", "private"]
		current_values = frappe.db.get_value(doctype, record, fields)

		for field, value in zip(fields, current_values):
			value = ceil(cint(value) / (1024**2))
			frappe.get_doc(doctype, record).db_set(field, value, update_modified=False)

	frappe.db.commit()
	frappe.db.auto_commit_on_many_writes = scheme_before
	print(f"{total} {doctype} records updated")
