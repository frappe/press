# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class SiteConfigKeyBlacklist(Document):
	def validate(self):
		import frappe

		if frappe.db.exists("Site Config Key", {"key": self.key, "enabled": True}):
			frappe.msgprint(f"Key {self.key} exists in Site Config Key. This means that ")
