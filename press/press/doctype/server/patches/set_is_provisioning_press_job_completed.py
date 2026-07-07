# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
import frappe


def execute():
	frappe.db.set_value(
		"Server",
		{"is_provisioning_press_job_completed": 0},
		"is_provisioning_press_job_completed",
		1,
	)
	frappe.db.set_value(
		"Database Server",
		{"is_provisioning_press_job_completed": 0},
		"is_provisioning_press_job_completed",
		1,
	)
