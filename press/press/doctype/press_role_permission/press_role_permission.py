# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist


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

	dashboard_fields = ["site", "release_group", "server", "role"]

	def before_insert(self):
		if not frappe.local.system_user() and frappe.session.user != frappe.db.get_value(
			"Team", self.team, "user"
		):
			frappe.throw("Only the team owner can create role permissions")

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
			frappe.throw("Role Permission already exists")

	@dashboard_whitelist()
	def delete(self):
		if not frappe.local.system_user() and frappe.session.user != frappe.get_cached_value(
			"Team", self.team, "user"
		):
			frappe.throw("Only the team owner can delete this role permission")

		super().delete()
