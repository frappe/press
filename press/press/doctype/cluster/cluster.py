# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class Cluster(Document):
	def validate(self):
		self.defaults = frappe.get_all(
			self.doctype, {"default": 1, "name": ("!=", self.name)}
		)
		if not self.defaults:
			self.default = 1

	def on_update(self):
		if self.default and self.defaults:
			for cluster in self.defaults:
				frappe.db.set_value(self.doctype, cluster.name, "default", False)
