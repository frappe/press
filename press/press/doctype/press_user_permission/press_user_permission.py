# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressUserPermission(Document):
	pass


def has_user_permission(doc, name, action, groups):
	# is part of a group that has perm
	allowed = False

	group_perm = frappe.get_value(
		"Press User Permission",
		{
			"type": "Group",
			"group": ("in", groups),
			"document_type": doc,
			"document_name": name,
			"action": action,
		},
	)
	if group_perm:
		allowed = True

	# user has granular perm
	user_perm = frappe.get_value(
		"Press User Permission",
		{
			"type": "User",
			"user": frappe.session.user,
			"document_type": doc,
			"document_name": name,
			"action": action,
		},
	)
	if user_perm:
		allowed = True

	return allowed
