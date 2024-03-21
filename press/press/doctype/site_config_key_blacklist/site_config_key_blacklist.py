# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class SiteConfigKeyBlacklist(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		key: DF.Data
		reason: DF.SmallText | None
	# end: auto-generated types

	def validate(self):
		import frappe

		if frappe.db.exists("Site Config Key", {"key": self.key, "enabled": True}):
			frappe.msgprint(f"Key {self.key} exists in Site Config Key. This means that ")
