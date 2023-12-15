# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

from typing import Dict
import frappe
from frappe.model.document import Document

ALLOWED_CONFIG_PERMS = ["global", "restricted"]


class PressUserPermission(Document):
	def validate(self):
		if self.type == "Config":
			self.validate_config()

	def validate_config(self):
		config = frappe.parse_json(self.config)
		if not set(config.keys()).issubset(set(ALLOWED_CONFIG_PERMS)):
			frappe.throw(f"Invalid config key. Allowed keys are: {format(ALLOWED_CONFIG_PERMS)}")


def has_user_permission(doc: str, name: str, action: str, groups: list = None):
	groups = groups or []
	user = frappe.session.user
	allowed = False

	if not groups:
		groups = frappe.get_all(
			"Press Permission Group User", {"user": user}, pluck="parent"
		)

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
			"user": user,
			"document_type": doc,
			"document_name": name,
			"action": action,
		},
	):
		allowed = True

	# has config perm access
	config = frappe.db.get_value(
		"Press User Permission", {"user": user, "type": "Config"}, "config", as_dict=True
	)
	if config:
		allowed = check_config_perm(
			frappe.parse_json(config["config"]), doc, name, action, allowed
		)

	return allowed


def check_config_perm(
	config: Dict, doctype: str, name: str, action: str, allowed: bool
):
	perm_types = config.keys()

	if "global" in perm_types:
		allowed = has_config_perm(config["global"], doctype, name, action, allowed, "global")

	if "restricted" in perm_types:
		allowed = has_config_perm(
			config["restricted"], doctype, name, action, allowed, "restricted"
		)

	return allowed


def has_config_perm(
	config: Dict, doctype: str, name: str, action: str, allowed: bool, ptype: str
):
	if doctype in config.keys():
		docnames = config[doctype].keys()
		if name in docnames:
			name = name
		elif "*" in docnames:
			name = "*"
		else:
			return allowed

		if action in config[doctype][name] or "*" in config[doctype][name]:
			if ptype == "restricted":
				allowed = False
			elif ptype == "global":
				allowed = True

	return allowed
