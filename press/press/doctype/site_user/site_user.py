# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SiteUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		site: DF.Link
		user: DF.Data
	# end: auto-generated types

	def login_to_site(self):
		"""Login to the site."""

		site = frappe.get_doc("Site", self.site)
		return site.login_as_user(self.user)


def create_user_for_product_site(site, data):
	analytics = data["analytics"]
	users_data = analytics.get("users", [])
	for user_data in users_data:
		user_mail = user_data.get("email")
		enabled = user_data.get("enabled")
		if frappe.db.exists("Site User", {"site": site, "user": user_mail}):
			user = frappe.db.get_value(
				"Site User", {"site": site, "user": user_mail}, ["name", "enabled"], as_dict=True
			)
			if user.enabled != enabled:
				frappe.db.set_value("Site User", user.name, "enabled", enabled)
		else:
			user = frappe.get_doc(
				{"doctype": "Site User", "site": site, "user": user_mail, "enabled": enabled}
			)
			user.insert(ignore_permissions=True)
