# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PressUserPermission(Document):
	pass


def has_user_permission(doc, name, action, groups):
	allowed = False

	# part of a group with access
	if frappe.db.exists(
		"Press User Permission",
		{
			"type": "Group",
			"group": ("in", groups),
			"document_type": doc,
			"document_name": name,
			"action": action,
		},
	):
		allowed = True

	# user has granular perm access
	if frappe.db.exists(
		"Press User Permission",
		{
			"type": "User",
			"user": frappe.session.user,
			"document_type": doc,
			"document_name": name,
			"action": action,
		},
	):
		allowed = True

	return allowed
