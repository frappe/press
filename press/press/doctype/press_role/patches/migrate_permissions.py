# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

import frappe

from press.utils import _system_user


def execute():
	frappe.local.system_user = _system_user

	teams = frappe.get_all(
		"Team",
		filters={"enabled": 1},
		pluck="name",
	)
	for team in teams:
		migrate_group_permissions(team)


def migrate_group_permissions(team):
	groups = frappe.qb.get_query(
		"Press Permission Group",
		fields=["name", "title", "team", {"users": ["user"]}],
		filters={"team": team},
	).run(as_dict=1)

	for group in groups:
		old_group_permissions = frappe.get_all(
			"Press User Permission",
			filters={"group": group.name, "type": "Group"},
			fields=["document_type", "document_name"],
			distinct=True,
		)

		if not old_group_permissions:
			continue

		if frappe.db.exists("Press Role", {"title": group.title, "team": group.team}):
			continue

		role = frappe.new_doc("Press Role")
		role.title = group.title
		role.team = team
		role.enable_billing = 1
		role.enable_apps = 1
		for row in group.users:
			role.append("users", {"user": row.user})
		role.insert()

		for perm in old_group_permissions:
			if perm.document_type not in ["Site", "Release Group", "Server"]:
				continue
			fieldname = perm.document_type.lower().replace(" ", "_")
			frappe.get_doc(
				{
					"doctype": "Press Role Permission",
					"role": role.name,
					"team": team,
					fieldname: perm.document_name,
				}
			).insert()
