# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe

from press.utils import _system_user
from frappe.model.document import bulk_insert


def execute():
	frappe.local.system_user = _system_user

	teams = frappe.get_all("Team", pluck="name", filters={"enabled": 1})
	for team in teams:
		migrate_permissions(team)


def migrate_permissions(team):

	groups = frappe.get_all(
		"Press Permission Group", fields=["name", "title"], filters={"team": team}
	)

	for group in groups:
		group_doc = frappe.get_doc("Press Permission Group", group.name)

		perms = frappe.get_all(
			"Press User Permission",
			filters={"group": group.name, "type": "Group"},
			fields=["document_type", "document_name"],
			distinct=True,
		)

		if not perms:
			continue

		if frappe.db.exists("Press Role", {"title": group_doc.title, "team": team}):
			continue

		role = frappe.new_doc("Press Role")
		role.title = group_doc.title
		role.team = team
		for user in group_doc.users:
			role.append("users", {"user": user.user})
		role.insert()

		permissions = []
		for perm in perms:
			if perm.document_type not in ["Site", "Release Group", "Server"]:
				continue

			# enable perms for all documents allowed in user permission for that particular role
			role = frappe.get_value("Press Role", {"title": group.title, "team": team})
			doc_field = perm.document_type.lower().replace(" ", "_")
			# frappe.get_doc({
			# 	"doctype": "Press Role Permission",
			# 	"role": role,
			# 	"team": group.team,
			# 	doc_field: perm.document_name,
			# }).insert()

			permissions.append(
				frappe.get_doc(
					{
						"doctype": "Press Role Permission",
						"role": role,
						"team": team,
						doc_field: perm.document_name,
					}
				)
			)

		bulk_insert("Press Role Permission", permissions, ignore_duplicates=True)
