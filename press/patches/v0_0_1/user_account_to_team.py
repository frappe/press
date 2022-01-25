# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe


def execute():
	frappe.reload_doc("press", "doctype", "site")
	frappe.reload_doc("press", "doctype", "account_request")
	frappe.reload_doc("press", "doctype", "team")
	frappe.reload_doc("press", "doctype", "team_member")

	user_accounts = frappe.db.sql(
		"SELECT user, account_key, creation FROM `tabUser Account`", as_dict=1
	)
	enabled_users = [d.name for d in frappe.db.get_all("User", {"enabled": 1}, ["name"])]

	users = [d.user for d in user_accounts]
	# create team for Administrator too
	if "Administrator" not in users:
		user_accounts.append(frappe._dict({"user": "Administrator"}))

	for d in user_accounts:
		if not d.user:
			continue
		# create team
		team = frappe.new_doc("Team")
		team.name = d.user
		team.append("team_members", {"user": d.user})
		team.enabled = d.user in enabled_users
		team.creation = d.creation
		team.modified = d.modified
		team.insert()

		# create account request
		if d.account_key:
			account_request = frappe.new_doc("Account Request")
			account_request.request_key = d.account_key
			account_request.email = d.user
			account_request.team = d.user
			account_request.role = "Press Admin"
			account_request.creation = d.creation
			account_request.insert()

		# update team in sites
		frappe.db.update("Site", {"owner": d.user}, "team", team.name)

	frappe.delete_doc_if_exists("DocType", "User Account")
