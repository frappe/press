# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe


def execute():
	migrate_users_from_group_to_role()
	migrate_permissions_from_group_to_role()


def migrate_users_from_group_to_role():
	groups = frappe.get_all(
		"Press Permission Group",
		pluck="name",
	)
	for group in groups:
		group_doc = frappe.get_doc("Press Permission Group", group)
		role = frappe.new_doc("Press Role")
		role.role = group_doc.title
		role.team = group_doc.team
		group_users = frappe.get_all(
			"Press Permission Group User",
			filters={"parent": group},
			pluck="user",
		)
		role.append("users", [{"user": user} for user in group_users])
		role.save()


def migrate_permissions_from_group_to_role():
	pass
