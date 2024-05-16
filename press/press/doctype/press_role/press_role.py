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
