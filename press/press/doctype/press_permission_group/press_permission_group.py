# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Count

DEFAULT_PERMISSIONS = {
	"*": {
		"*": {
			"allow": ["*"],
			"restrict": [],
		}
	}
}


class PressPermissionGroup(Document):
	@staticmethod
	def get_list_query(query):
		Group = frappe.qb.DocType("Press Permission Group")
		GroupUser = frappe.qb.DocType("Press Permission Group User")

		user_count = (
			frappe.qb.from_(GroupUser)
			.select(Count(GroupUser.user))
			.where(GroupUser.parent == Group.name)
		)

		query = query.where(Group.team == frappe.local.team().name).select(
			user_count.as_("user_count")
		)

		return query

	def validate(self):
		self.validate_permissions()

	def validate_permissions(self):
		permissions = frappe.parse_json(self.permissions)
		if not permissions:
			self.permissions = DEFAULT_PERMISSIONS
			return

		RESTRICTED_DOCTYPES = frappe.get_all(
			"Press Method Permission", pluck="document_type", distinct=True
		)

		for doctype, doctype_perms in permissions.items():
			if doctype == "*":
				continue

			if doctype not in RESTRICTED_DOCTYPES:
				frappe.throw(f"{doctype} is not a valid doctype.")

			if not isinstance(doctype_perms, dict):
				frappe.throw(
					f"Invalid perms for {doctype}. Rule must be key-value pairs of document name and document perms."
				)

			for document_name, document_perms in doctype_perms.items():
				if document_name == "*":
					continue

				if not isinstance(document_perms, dict):
					frappe.throw(
						f"Invalid perms for {doctype} > {document_name}. Rule must be key-value pairs of allow or restrict."
					)

				allowed = document_perms.get("allow", None)
				restricted = document_perms.get("restrict", None)
				if allowed and not isinstance(allowed, list):
					frappe.throw(
						f"Invalid allow value for {doctype} > {document_name}. Allow must be a list."
					)
				if restricted and not isinstance(restricted, list):
					frappe.throw(
						f"Invalid restrict value for {doctype} > {document_name}. Restrict must be a list."
					)

				# TODO: validate allow and restrict values


def has_user_permission(doctype: str, name: str, method: str, group_names: list = None):
	user = frappe.session.user
	allowed = False

	RESTRICTED_DOCTYPES = frappe.get_all(
		"Press Method Permission", pluck="document_type", distinct=True
	)

	if doctype not in RESTRICTED_DOCTYPES:
		return True

	if not group_names:
		group_names = get_permission_groups(user)

	for group_name in set(group_names):
		user_belongs_to_group = frappe.db.exists(
			"Press Permission Group User", {"parent": group_name, "user": user}
		)
		if not user_belongs_to_group:
			continue

		permissions = frappe.db.get_value(
			"Press Permission Group", group_name, "permissions"
		)
		permissions = frappe.parse_json(permissions)
		doctype_perms = permissions.get(doctype, None) or permissions.get("*", None)
		if not doctype_perms:
			allowed = True
			continue

		document_perms = doctype_perms.get(name, None) or doctype_perms.get("*", None)
		if not document_perms:
			allowed = True
			continue

		allowed_methods = document_perms.get("allow", None)
		restricted_methods = document_perms.get("restrict", None)
		if not allowed_methods and not restricted_methods:
			allowed = True

		if allowed_methods and (method in allowed_methods or "*" in allowed_methods):
			allowed = True

		if (
			restricted_methods
			and method not in restricted_methods
			and "*" not in restricted_methods
		):
			allowed = True

	return allowed


def get_permission_groups(user: str = None) -> list:
	if not user:
		user = frappe.session.user

	return frappe.get_all(
		"Press Permission Group User",
		filters={"user": user},
		pluck="parent",
		distinct=True,
	)


def get_permitted_methods(doctype: str, name: str, group_names: list = None) -> list:
	permitted_methods = []
	user = frappe.session.user
	permission_groups = group_names or get_permission_groups(user)
	for group_name in set(permission_groups):
		permissions = frappe.db.get_value("Press Permission Group", group_name, "permissions")
		if not permissions:
			continue
		permissions = frappe.parse_json(permissions)
		doctype_perms = permissions.get(doctype, None) or permissions.get("*", None)
		if not doctype_perms:
			continue

		document_perms = doctype_perms.get(name, None) or doctype_perms.get("*", None)
		if not document_perms:
			continue

		allowed_methods = document_perms.get("allow", None)
		restricted_methods = document_perms.get("restrict", None)
		if allowed_methods:
			permitted_methods += allowed_methods
		if restricted_methods:
			permitted_methods = [
				method
				for method in permitted_methods
				if method not in restricted_methods
			]

	return permitted_methods


@frappe.whitelist()
def get_permissions(group_name: str = None):
	from press.api.client import get_list

	user = frappe.session.user
	team = frappe.local.team().name

	restrictable_methods = frappe.get_all(
		"Press Method Permission", fields=["document_type", "checkbox_label", "method"]
	)

	document_types = set(method.document_type for method in restrictable_methods)

	options = []
	for doctype in document_types:
		fields = ["name", "title"] if doctype != "Site" else ["name"]
		docs = get_list(
			doctype=doctype,
			fields=fields,
			filters={"team": team},
		)

		for doc in docs:
			permitted_methods = get_permitted_methods(
				doctype, doc.name, group_names=[group_name]
			)
			options.append(
				{
					"document_type": doctype,
					"document_name": doc.name,
					"permissions": [
						{
							"method": d.method,
							"label": d.checkbox_label,
							"permitted": d.method in permitted_methods
							or "*" in permitted_methods,
						}
						for d in restrictable_methods
						if d.document_type == doctype
					],
				}
			)

	return options
