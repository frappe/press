# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# Proprietary License. See license.txt


import frappe


def execute():
	for d in frappe.db.get_all("Team"):
		team = frappe.get_doc("Team", d.name)
		if team.has_partner_account_on_erpnext_com():
			team.enable_erpnext_partner_privileges()
