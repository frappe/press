# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from press.api.client import dashboard_whitelist


class PressRole(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from press.press.doctype.press_role_user.press_role_user import PressRoleUser

		enable_apps: DF.Check
		enable_billing: DF.Check
		team: DF.Link
		title: DF.Data
		users: DF.Table[PressRoleUser]
	# end: auto-generated types

	dashboard_fields = ["title", "users", "enable_billing", "enable_apps", "team"]

	def before_insert(self):
		if not frappe.local.system_user() and frappe.session.user != frappe.db.get_value(
			"Team", self.team, "user"
		):
			frappe.throw("Only the team owner can create roles")

	@dashboard_whitelist()
	def add_user(self, user):
		user_exists = self.get("users", {"user": user})
		if user_exists:
			frappe.throw(f"{user} already belongs to {self.title}")

		self.append("users", {"user": user})
		self.save()

	@dashboard_whitelist()
	def remove_user(self, user):
		user_exists = self.get("users", {"user": user})
		if not user_exists:
			frappe.throw(f"{user} does not belong to {self.title}")

		for row in self.users:
			if row.user == user:
				self.remove(row)
				break
		self.save()

	@dashboard_whitelist()
	def delete_permissions(self, permissions: list[str]) -> None:
		for perm in permissions:
			perm_doc = frappe.get_doc("Press Role Permission", perm)
			if perm_doc.role == self.name:
				perm_doc.delete()

	@dashboard_whitelist()
	def delete(self):
		if not frappe.local.system_user() and frappe.session.user != frappe.db.get_value(
			"Team", self.team, "user"
		):
			frappe.throw("Only the team owner can delete this role")

		super().delete()

	def on_trash(self):
		frappe.db.delete("Press Role Permission", {"role": self.name})


def check_role_permissions(doctype: str, name: str | None = None) -> list[str] | None:
	"""
	Check if the user is permitted to access the document
	Expects the function to throw error for `get` or return a list of permitted roles for `get_list`

	:param doctype: Document type
	:param name: Document name
	:return: List of permitted roles or None
	"""
	if frappe.local.system_user():
		return []

	PressRoleUser = frappe.qb.DocType("Press Role User")
	PressRole = frappe.qb.DocType("Press Role")

	roles = (
		frappe.qb.from_(PressRole)
		.select(PressRole.name)
		.join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.where(PressRoleUser.user == frappe.session.user)
		.where(PressRole.team == frappe.local.team().name)
	).run(as_dict=1, pluck="name")

	if doctype in ["Site", "Release Group", "Server"]:
		field = doctype.lower().replace(" ", "_")
		if role_perms := frappe.get_all(
			"Press Role Permission",
			fields=["name", field],
			filters={"role": ("in", roles)},
		):
			# throw error if the user is not permitted for the document
			if name and not any(perm[field] == name for perm in role_perms):
				frappe.throw("Not permitted", frappe.PermissionError)
			else:
				return roles

	# throw error if any of the roles don't have permission for apps
	elif doctype == "Marketplace App":
		if not any(
			frappe.get_all(
				"Press Role",
				fields=["enable_apps"],
				filters={"name": ("in", roles)},
				pluck="enable_apps",
			)
		):
			frappe.throw("Not permitted", frappe.PermissionError)

	return []
