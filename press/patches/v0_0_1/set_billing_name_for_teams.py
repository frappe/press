# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe


def execute():
	scheme_before = frappe.db.auto_commit_on_many_writes
	frappe.db.auto_commit_on_many_writes = True
	frappe.reload_doc("press", "doctype", "team")

	teams = frappe.get_all("Team", pluck="name")
	for team in teams:
		frappe.get_doc("Team", team).save()

	frappe.db.auto_commit_on_many_writes = scheme_before
