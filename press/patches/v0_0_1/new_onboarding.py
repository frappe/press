# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


import frappe
from frappe.utils import update_progress_bar


def execute():
	frappe.reload_doc("press", "doctype", "team")
	frappe.reload_doc("press", "doctype", "team_onboarding")

	teams = frappe.db.get_all("Team")
	for i, team in enumerate(teams):
		update_progress_bar("Updating onboarding", i, len(teams))

		doc = frappe.get_doc("Team", team)

		if doc.onboarding:
			continue

		doc.initialize_onboarding_steps()

		if doc.erpnext_partner:
			update_onboarding(doc, "Add Billing Information", "Skipped")
			update_onboarding(doc, "Transfer Credits", "Skipped")
			update_onboarding(doc, "Create Site", "Skipped")

		if doc.default_payment_method:
			update_onboarding(doc, "Add Billing Information", "Completed")

		if frappe.db.count("Site", {"team": doc.name}) > 0:
			update_onboarding(doc, "Create Site", "Completed")

		doc.save()

	print()


def update_onboarding(team, step_name, status):
	for step in team.onboarding:
		if step.step_name == step_name:
			step.status = status
