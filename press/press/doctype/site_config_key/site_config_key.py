# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class SiteConfigKey(Document):
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
