# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder.functions import Count

DEFAULT_PERMISSIONS = {
	"*": {"*": {"*": True}}  # all doctypes  # all documents  # all methods
}


class PressPermissionGroup(Document):
	whitelisted_fields = ["title"]

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
		self.validate_users()

	def validate_permissions(self):
		permissions = frappe.parse_json(self.permissions)
		if not permissions:
			self.permissions = DEFAULT_PERMISSIONS
			return

		for doctype, doctype_perms in permissions.items():
			if doctype not in get_all_restrictable_doctypes() and doctype != "*":
				frappe.throw(f"{doctype} is not a valid doctype.")

			if not isinstance(doctype_perms, dict):
				frappe.throw(
					f"Invalid perms for {doctype}. Rule must be key-value pairs of document name and document perms."
				)

			for doc_name, doc_perms in doctype_perms.items():
				if not isinstance(doc_perms, dict):
					frappe.throw(
						f"Invalid perms for {doctype} {doc_name}. Rule must be key-value pairs of method and permission."
					)

				if doctype == "*":
					continue

				restrictable_methods = get_all_restrictable_methods(doctype)
				if not restrictable_methods:
					frappe.throw(f"{doctype} does not have any restrictable methods.")

				for method, permitted in doc_perms.items():
					if method != "*" and method not in restrictable_methods:
						frappe.throw(f"{method} is not a valid method for {doctype}.")

	def validate_users(self):
		for user in self.users:
			if user.user == "Administrator":
				continue
			user_belongs_to_team = frappe.db.exists(
				"Team Member", {"parent": self.team, "user": user.user}
			)
			if not user_belongs_to_team:
				frappe.throw(f"{user.user} does not belong to {self.team}")

	@frappe.whitelist()
	def get_users(self):
		from press.api.client import get_list

		user_names = [user.user for user in self.users]
		if not user_names:
			return []

		return get_list(
			"User",
			filters={"name": ["in", user_names], "enabled": 1},
			fields=[
				"name",
				"first_name",
				"last_name",
				"full_name",
				"user_image",
				"name as email",
			],
		)

	@frappe.whitelist()
	def add_user(self, user):
		user_belongs_to_team = frappe.db.exists(
			"Team Member", {"parent": self.team, "user": user}
		)
		if not user_belongs_to_team:
			frappe.throw(f"{user} does not belong to {frappe.local.team().team_title}")

		user_belongs_to_group = self.get("users", {"user": user})
		if user_belongs_to_group:
			frappe.throw(f"{user} already belongs to {self.title}")

		self.append("users", {"user": user})
		self.save()

	@frappe.whitelist()
	def remove_user(self, user):
		user_belongs_to_group = self.get("users", {"user": user})
		if not user_belongs_to_group:
			frappe.throw(f"{user} does not belong to {self.name}")

		for row in self.users:
			if row.user == user:
				self.remove(row)
				break
		self.save()

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

		if doctype not in get_all_restrictable_doctypes():
			frappe.throw(f"{doctype} is not a valid restrictable doctype.")

		options = []
		fields = ["name", "title"] if doctype != "Site" else ["name"]
		docs = get_list(doctype=doctype, fields=fields)

		restrictable_methods = get_all_restrictable_methods(doctype)
		if not restrictable_methods:
			frappe.throw(f"{doctype} does not have any restrictable methods.")

		for doc in docs:
			permitted_methods = get_permitted_methods(doctype, doc.name, group_names=[self.name])
			doc_perms = []
			for method, label in restrictable_methods.items():
				is_permitted = method in permitted_methods
				doc_perms.append(
					{
						"label": label,
						"method": method,
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


def has_method_permission(
	doctype: str, name: str, method: str, group_names: list = None
):
	user = frappe.session.user

	if doctype not in get_all_restrictable_doctypes():
		return True

	if method not in get_all_restrictable_methods(doctype):
		return True

	if not group_names:
		group_names = get_permission_groups(user)

	if not group_names:
		# user does not have any restricted permissions set in any group
		return True

	if method in get_permitted_methods(doctype, name, group_names):
		return True

	return False


def get_permitted_methods(doctype: str, name: str, group_names: list = None) -> list:
	user = frappe.session.user

	if doctype not in get_all_restrictable_doctypes():
		frappe.throw(f"{doctype} is not a valid restrictable doctype.")

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

	all_methods = get_all_restrictable_methods(doctype)
	all_allowed = {method: True for method in all_methods}
	all_restricted = {method: False for method in all_methods}

	if not permissions:
		# this group allows all methods of all documents
		return all_allowed

	permissions = frappe.parse_json(permissions)
	doctype_perms = permissions.get(doctype, None) or permissions.get("*", None)
	if not doctype_perms:
		# this group allows all methods of all documents
		return all_allowed

	doc_perms = doctype_perms.get(name, None) or doctype_perms.get("*", None)
	if not doc_perms:
		# this group allows all methods of this document
		return all_allowed

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


def get_all_restrictable_methods(doctype: str) -> list:
	methods = {
		"Site": {
			# method: label,
			"archive": "Drop",
			"migrate": "Migrate",
			"activate": "Activate",
			"reinstall": "Reinstall",
			"deactivate": "Deactivate",
			"enable_database_access": "Database",
			"restore_site_from_files": "Restore",
		},
		"Release Group": {
			"restart": "Restart",
		},
	}
	return methods.get(doctype, {})


def get_all_restrictable_doctypes() -> list:
	return list(get_all_restrictable_methods().keys())


def get_permission_groups(user: str = None) -> list:
	if not user:
		user = frappe.session.user

	return frappe.get_all(
		"Press Permission Group User",
		filters={"user": user},
		pluck="parent",
		distinct=True,
	)
