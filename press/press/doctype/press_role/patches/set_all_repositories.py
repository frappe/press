# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

import frappe


def execute():
	PressRole = frappe.qb.DocType("Press Role")
	frappe.qb.update(PressRole).set(PressRole.all_repositories, 1).run()
