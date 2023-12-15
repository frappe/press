# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Count

DEFAULT_PERMISSIONS = {
	"*": {"*": {"*": True}}  # all doctypes  # all documents  # all methods
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
			if doctype not in RESTRICTED_DOCTYPES and doctype != "*":
				frappe.throw(f"{doctype} is not a valid doctype.")

			if not isinstance(doctype_perms, dict):
				frappe.throw(
					f"Invalid perms for {doctype}. Rule must be key-value pairs of document name and document perms."
				)

			for doc_name, doc_perms in doctype_perms.items():
				if not isinstance(doc_perms, dict):
					frappe.throw(
						f"Invalid perms for {doctype} > {doc_name}. Rule must be key-value pairs of allow or restrict."
					)

				# TODO: validate allow and restrict values

	@frappe.whitelist()
	def get_permissions(self, doctype: str) -> list:
		"""
		Get the permissions for the specified document type or all restrictable document types.

		:param doctype: The doctype for which permissions are to be retrieved.
		:return: A list of dictionaries containing the document type, document name, and permissions for each document.
		"""
		from press.api.client import get_list

		user = frappe.session.user
		user_belongs_to_group = self.get("users", {"user": user})
		if not user_belongs_to_group and user != "Administrator":
			frappe.throw(f"{user} does not belong to {self.name}")

		restrictable_methods = frappe.get_all(
			"Press Method Permission",
			fields=["document_type", "checkbox_label", "method"],
			distinct="method",
		)
		restrictable_doctypes = set(method.document_type for method in restrictable_methods)
		if doctype and doctype not in restrictable_doctypes:
			frappe.throw(f"Create a Press Method Permission for {doctype} to restrict it.")

		options = []
		fields = ["name", "title"] if doctype != "Site" else ["name"]
		docs = get_list(doctype=doctype, fields=fields)

		for doc in docs:
			permitted_methods = get_permitted_methods(doctype, doc.name, group_names=[self.name])
			doc_perms = []
			for ui_action in restrictable_methods:
				if ui_action.document_type == doctype:
					is_permitted = ui_action.method in permitted_methods
					doc_perms.append(
						{
							"method": ui_action.method,
							"label": ui_action.checkbox_label,
							"permitted": is_permitted,
						}
					)
			options.append(
				{
					"document_type": doctype,
					"document_name": doc.name,
					"permissions": doc_perms,
				}
			)

		return options

	@frappe.whitelist()
	def update_permissions(self, updated_permissions):
		cur_permissions = frappe.parse_json(self.permissions)
		for updated_doctype, updated_doctype_perms in updated_permissions.items():
			if updated_doctype not in cur_permissions:
				cur_permissions[updated_doctype] = {}

			for updated_docname, updated_docperms in updated_doctype_perms.items():
				if updated_docname == "*":
					cur_permissions[updated_doctype] = {"*": updated_docperms}
					continue
				if updated_docname not in cur_permissions[updated_doctype]:
					cur_permissions[updated_doctype][updated_docname] = {}

				for method, permitted in updated_docperms.items():
					cur_permissions[updated_doctype][updated_docname][method] = permitted

		self.permissions = cur_permissions
		self.save()

	@frappe.whitelist()
	def get_users(self):
		user_names = [user.user for user in self.users]
		if not user_names:
			return []
		return frappe.get_list(
			"User",
			filters={"name": ["in", user_names], "enabled": 1},
			fields=["name", "first_name", "last_name", "full_name", "user_image"],
		)


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

		group_perms = frappe.db.get_value("Press Permission Group", group_name, "permissions")
		group_perms = frappe.parse_json(group_perms)
		doctype_perms = group_perms.get(doctype, None) or group_perms.get("*", None)
		if not doctype_perms:
			allowed = True
			continue

		doc_perms = doctype_perms.get(name, None) or doctype_perms.get("*", None)
		if not doc_perms:
			allowed = True
			continue

		method_perm = doc_perms.get(method, None) or doc_perms.get("*", None)
		allowed = True if method_perm is None else method_perm

	return allowed


def get_permitted_methods(doctype: str, name: str, group_names: list = None) -> list:
	user = frappe.session.user

	if not frappe.db.exists("Press Method Permission", {"document_type": doctype}):
		frappe.throw(f"Create a Press Method Permission for {doctype} to restrict it.")

	permissions_by_group = {}
	permission_groups = group_names or get_permission_groups(user)
	for group_name in set(permission_groups):
		permissions_by_group[group_name] = get_method_perms_for_group(
			doctype, name, group_name
		)

	permitted_methods = []
	for group_name, method_perms in permissions_by_group.items():
		for method, permitted in method_perms.items():
			if permitted:
				permitted_methods.append(method)

	return list(set(permitted_methods))


def get_method_perms_for_group(doctype: str, name: str, group_name: str) -> list:
	permissions = frappe.db.get_value("Press Permission Group", group_name, "permissions")
	if not permissions:
		# this group allows all methods of all documents
		return {"*": True}

	permissions = frappe.parse_json(permissions)
	doctype_perms = permissions.get(doctype, None) or permissions.get("*", None)
	if not doctype_perms:
		# this group allows all methods of all documents
		return {"*": True}

	doc_perms = doctype_perms.get(name, None) or doctype_perms.get("*", None)
	if not doc_perms:
		# this group allows all methods of this document
		return {"*": True}

	all_methods = get_all_restrictable_methods(doctype)
	all_allowed = {method: True for method in all_methods}
	all_restricted = {method: False for method in all_methods}

	wildcard_not_present = doc_perms.get("*", None) is None
	wildcard_restricted = doc_perms.get("*", None) is False
	wildcard_allowed = doc_perms.get("*", None) is True

	if wildcard_not_present or wildcard_restricted:
		# * not present so only allow or restrict those that are explicitly false
		# OR all methods are restricted except those that are explicitly true
		for method, permitted in all_restricted.items():
			if method in doc_perms and doc_perms[method]:
				all_restricted[method] = True
		return all_restricted

	elif wildcard_allowed:
		# all methods are allowed except those that are explicitly false
		for method, permitted in all_allowed.items():
			if method in doc_perms and not doc_perms[method]:
				all_allowed[method] = False
		return all_allowed


def get_all_restrictable_methods(doctype: str = None) -> list:
	filters = {}
	if doctype:
		filters["document_type"] = doctype
	else:
		filters["document_type"] = [
			"in",
			frappe.get_all("Press Method Permission", pluck="document_type", distinct=True),
		]

	return frappe.get_all(
		"Press Method Permission",
		filters=filters,
		pluck="method",
	)


def get_permission_groups(user: str = None) -> list:
	if not user:
		user = frappe.session.user

	return frappe.get_all(
		"Press Permission Group User",
		filters={"user": user},
		pluck="parent",
		distinct=True,
	)
