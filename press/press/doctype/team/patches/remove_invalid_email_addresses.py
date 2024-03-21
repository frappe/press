# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe
from frappe.utils import update_progress_bar, validate_email_address


def execute():
	emails = frappe.get_all(
		"Communication Email",
		{"parentfield": "communication_emails", "parenttype": "Team", "value": ("is", "set")},
		["name", "value"],
	)

	total_emails = len(emails)
	for index, email in enumerate(emails):
		update_progress_bar("Updating emails", index, total_emails)
		if not validate_email_address(email.value):
			frappe.db.set_value("Communication Email", email.name, "", update_modified=False)
