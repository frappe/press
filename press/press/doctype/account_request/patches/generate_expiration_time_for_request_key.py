# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe


def execute():
	frappe.db.set_value(
		"Account Request",
		{
			"request_key_expiration_time": ("is", "not set"),
			"request_key": ["is", "set"],
		},
		{
			"request_key_expiration_time": frappe.utils.add_to_date(None, minutes=10),
		},
		update_modified=False,
	)
