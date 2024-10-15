# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

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

		admin_access: DF.Check
		allow_apps: DF.Check
		allow_bench_creation: DF.Check
		allow_billing: DF.Check
		allow_partner: DF.Check
		allow_server_creation: DF.Check
		allow_site_creation: DF.Check
		allow_webhook_configuration: DF.Check
		team: DF.Link
		title: DF.Data
		users: DF.Table[PressRoleUser]
	# end: auto-generated types

	dashboard_fields = (
		"title",
		"users",
		"admin_access",
		"allow_billing",
		"allow_apps",
		"allow_partner",
		"allow_site_creation",
		"allow_bench_creation",
		"allow_server_creation",
		"allow_webhook_configuration",
		"team",
	)

	def before_insert(self):
		if frappe.db.exists("Press Role", {"title": self.title, "team": self.team}):
			frappe.throw(f"Role with title {self.title} already exists", frappe.DuplicateEntryError)

		if not frappe.local.system_user() and frappe.session.user != frappe.db.get_value(
			"Team", self.team, "user"
		):
			frappe.throw("Only the team owner can create roles")

	def validate(self):
		admin_roles = frappe.get_all(
			"Press Role",
			filters={"team": self.team, "admin_access": 1, "name": ("!=", self.name)},
		)
		if admin_roles and self.admin_access:
			frappe.throw("There can only be one admin role per team")

		if self.admin_access:
			self.allow_apps = 1
			self.allow_billing = 1
			self.allow_partner = 1
			self.allow_site_creation = 1
			self.allow_bench_creation = 1
			self.allow_server_creation = 1
			self.allow_webhook_configuration = 1

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
	def delete(self) -> None:
		if not frappe.local.system_user() and frappe.session.user != frappe.db.get_value(
			"Team", self.team, "user"
		):
			frappe.throw("Only the team owner can delete this role")

		super().delete()

	def on_trash(self) -> None:
		frappe.db.delete("Press Role Permission", {"role": self.name})
		frappe.db.delete("Account Request Press Role", {"press_role": self.name})


def check_role_permissions(doctype: str, name: str | None = None) -> list[str] | None:
	"""
	Check if the user is permitted to access the document based on the role permissions
	Expects the function to throw error for `get` if no permission and return a list of permitted roles for `get_list`
	Note: Empty list means no restrictions

	:param doctype: Document type
	:param name: Document name
	:return: List of permitted roles or None
	"""
	from press.utils import has_role

	if doctype not in [
		"Site",
		"Release Group",
		"Server",
		"Marketplace App",
		"Press Webhook",
		"Press Webhook Log",
		"Press Webhook Attempt",
	]:
		return []

	if (hasattr(frappe.local, "system_user") and frappe.local.system_user()) or has_role(
		"Press Support Agent"
	):
		return []

	PressRoleUser = frappe.qb.DocType("Press Role User")
	PressRole = frappe.qb.DocType("Press Role")
	query = (
		frappe.qb.from_(PressRole)
		.select(PressRole.name)
		.join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.where(PressRoleUser.user == frappe.session.user)
		.where(PressRole.team == frappe.local.team().name)
	)

	if (
		doctype == "Marketplace App"
		and (roles := query.select(PressRole.allow_apps).run(as_dict=1))
		and not any(perm.allow_apps for perm in roles)
	):
		# throw error if any of the roles don't have permission for apps
		frappe.throw("Not permitted", frappe.PermissionError)

	elif (
		doctype in ["Press Webhook", "Press Webhook Log", "Press Webhook Attempt"]
		and (roles := query.select(PressRole.allow_webhook_configuration).run(as_dict=1))
		and not any(perm.allow_webhook_configuration for perm in roles)
	):
		# throw error if any of the roles don't have permission for webhooks
		frappe.throw("Not permitted", frappe.PermissionError)

	elif doctype in ["Site", "Release Group", "Server"]:
		field = doctype.lower().replace(" ", "_")
		if roles := query.run(as_dict=1, pluck="name"):
			perms = frappe.db.get_all(
				"Press Role Permission",
				filters={"role": ["in", roles], field: name},
			)
			if not perms and name:
				# throw error if the user is not permitted for the document
				frappe.throw(
					f"You don't have permission to this {doctype if doctype != 'Release Group' else 'Bench'}",
					frappe.PermissionError,
				)
			else:
				return roles

	return []


def add_permission_for_newly_created_doc(doc: Document) -> None:
	"""
	Used to bulk insert permissions right after a site/release group/server is created
	for users with create permission for respective doctype is enabled
	"""

	doctype = doc.doctype
	if doctype not in ["Site", "Release Group", "Server"]:
		return

	role_fieldname = ""
	fieldname = doctype.lower().replace(" ", "_")
	if doctype == "Site":
		role_fieldname = "allow_site_creation"
	elif doctype == "Server":
		role_fieldname = "allow_server_creation"
	elif doctype == "Release Group":
		role_fieldname = "allow_bench_creation"

	new_perms = []
	PressRole = frappe.qb.DocType("Press Role")
	PressRoleUser = frappe.qb.DocType("Press Role User")
	if roles := (
		frappe.qb.from_(PressRole)
		.select(PressRole.name)
		.join(PressRoleUser)
		.on(PressRoleUser.parent == PressRole.name)
		.where(PressRoleUser.user == frappe.session.user)
		.where(PressRole.team == doc.team)
		.where(PressRole[role_fieldname] == 1)
		.run(as_dict=1, pluck="name")
	):
		for role in roles:
			new_perms.append(
				(
					frappe.generate_hash(length=12),
					role,
					doc.name,
					doc.team,
					frappe.utils.now(),
					frappe.utils.now(),
				)
			)

	if new_perms:
		frappe.db.bulk_insert(
			"Press Role Permission",
			fields=["name", "role", fieldname, "team", "creation", "modified"],
			values=set(new_perms),
		)
