# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt
from __future__ import annotations

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist
from press.utils import docs


class PressRolePermission(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		release_group: DF.Link | None
		role: DF.Link
		server: DF.Link | None
		site: DF.Link | None
		team: DF.Link
	# end: auto-generated types

	dashboard_fields = ("site", "release_group", "server", "role")

	def before_insert(self):
		if (
			not frappe.local.system_user()
			and frappe.session.user != frappe.db.get_value("Team", self.team, "user")
			and not is_user_part_of_admin_role()
		):
			frappe.throw(
				f"Only the team owner or an admin can create role permissions. Please ask a team admin to do this. {docs.doc_link(docs.ROLE_PERMISSIONS)}."
			)

		if frappe.db.exists(
			"Press Role Permission",
			{
				"role": self.role,
				"team": self.team,
				"site": self.site,
				"release_group": self.release_group,
				"server": self.server,
			},
		):
			frappe.throw(
				"This role already has a permission for this resource. Please edit the existing permission instead of adding a duplicate."
			)

	@dashboard_whitelist()
	def delete(self):
		if (
			not frappe.local.system_user()
			and frappe.session.user != frappe.get_cached_value("Team", self.team, "user")
			and not is_user_part_of_admin_role()
		):
			frappe.throw(
				f"Only the team owner or an admin can delete this role permission. Please ask a team admin to do this. {docs.doc_link(docs.ROLE_PERMISSIONS)}."
			)

		super().delete()


def is_user_part_of_admin_role(user: str | None = None) -> bool:
	"""Check if the user is part of any admin role."""
	from press.utils import get_current_team

	if not user:
		user = frappe.session.user

	team = get_current_team()

	admin_roles = frappe.get_all(
		"Press Role",
		filters={"team": team, "admin_access": 1},
		fields=["name"],
	)

	users = frappe.get_all(
		"Press Role User",
		filters={"parent": ["in", [role.name for role in admin_roles]], "user": user},
		fields=["name"],
	)

	return bool(users)
