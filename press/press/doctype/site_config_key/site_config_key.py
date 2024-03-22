# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class SiteConfigKey(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		internal: DF.Check
		key: DF.Data
		title: DF.Data | None
		type: DF.Literal["Password", "String", "Number", "Boolean", "JSON"]
	# end: auto-generated types

	dashboard_fields = ["key", "title", "description", "type"]

	def validate(self):
		import frappe

		if not self.title:
			self.title = self.key.replace("_", " ").title()

		if not self.internal and frappe.db.exists(
			"Site Config Key Blacklist", {"key": self.key}
		):
			frappe.throw(
				f"Key {self.key} is Blacklisted. Please contact Administrators to enable it."
			)
