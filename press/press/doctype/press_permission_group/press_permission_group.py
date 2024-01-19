# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

DEFAULT_PERMISSIONS = {
	"*": {"*": {"*": True}}  # all doctypes  # all documents  # all methods
}


class PressPermissionGroup(Document):
	whitelisted_fields = ["title"]

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
						frappe.throw(f"{method} is not a restrictable method of {doctype}")

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
		user_names = [user.user for user in self.users]
		if not user_names:
			return []

		return frappe.db.get_all(
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
	def get_all_document_permissions(self, doctype: str) -> list:
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

		restrictable_methods = get_all_restrictable_methods(doctype)
		if not restrictable_methods:
			frappe.throw(f"{doctype} does not have any restrictable methods.")

		options = []
		fields = ["name", "title"] if doctype != "Site" else ["name"]
		docs = get_list(doctype=doctype, fields=fields)
		print(docs)

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

	method_perms = resolve_doc_permissions(doctype, permissions_by_group)
	permitted_methods = [method for method, permitted in method_perms.items() if permitted]
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

	return doc_perms


def resolve_doc_permissions(doctype, permissions_by_group: dict) -> dict:
	"""
	Permission Resolution Logic:
	- if a group has *: True and another group has *: False, then all the methods are allowed
	- if a group has *: True and another group has 'method': False, then that method is restricted
	- if a group has 'method': True and another group has 'method': False, then that method is allowed
	"""
	method_perms = {}

	all_methods = get_all_restrictable_methods(doctype)
	all_restricted = {method: False for method in all_methods}
	all_allowed = {method: True for method in all_methods}

	# first we parse the wildcard permissions
	# if any group has *: True, then all methods are allowed
	for group_name, permissions in permissions_by_group.items():
		if permissions.get("*", None) is None:
			continue
		if permissions.get("*", None) is True:
			method_perms = all_allowed
			break
		if permissions.get("*", None) is False:
			method_perms = all_restricted

	# now we restrict all the methods that are explicitly restricted
	# so that we can allow all the methods that are explicitly allowed later
	for group_name, permissions in permissions_by_group.items():
		for method, permitted in permissions.items():
			if not permitted and method != "*":
				method_perms[method] = False

	# now we allow all the methods that are explicitly allowed
	for group_name, permissions in permissions_by_group.items():
		for method, permitted in permissions.items():
			if permitted and method != "*":
				method_perms[method] = True

	return method_perms


def get_all_restrictable_doctypes() -> list:
	return ["Site", "Release Group"]


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


def get_permission_groups(user: str = None) -> list:
	if not user:
		user = frappe.session.user

	return frappe.get_all(
		"Press Permission Group User",
		filters={"user": user},
		pluck="parent",
		distinct=True,
	)
