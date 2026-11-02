# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe


def execute():
	if not frappe.db.has_index("tabPress Job Step", "job_status_idx"):
		frappe.db.add_index("Press Job Step", ["job", "status"], "job_status_idx")
