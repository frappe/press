# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class SiteConfig(Document):
	def get_type(self):
		return frappe.db.get_value("Site Config Key", self.key, "type")
