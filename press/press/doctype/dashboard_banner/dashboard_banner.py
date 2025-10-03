# Copyright (c) 2024, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

from press.api.client import dashboard_whitelist


class DashboardBanner(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action: DF.Data | None
		action_label: DF.Data | None
		enabled: DF.Check
		has_action: DF.Check
		help_url: DF.Data | None
		is_dismissible: DF.Check
		is_global: DF.Check
		message: DF.Data | None
		server: DF.Link | None
		site: DF.Link | None
		team: DF.Link | None
		title: DF.Data | None
		type: DF.Literal["Info", "Success", "Error", "Warning"]
		type_of_scope: DF.Literal["Team", "Server", "Site"]
	# end: auto-generated types

	def validate(self):
		if self.is_global and self.is_dismissible:
			frappe.throw("Global banners cannot be dismissible.")

	@dashboard_whitelist()
	def dismiss(self):
		user = frappe.session.user
		if self.is_dismissible:
			frappe.get_doc(
				{
					"doctype": "Dashboard Banner Dismissal",
					"user": user,
					"dismissed_at": frappe.utils.now(),
					"dashboard_banner": self.name,
				}
			).insert()
			return True
		return False
